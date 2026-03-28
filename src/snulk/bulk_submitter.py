# Copyright (c) 2024 ServiceNow, Inc.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from __future__ import annotations # so we can used type references to classes that are not completely defined yet

from pathlib import Path
import logging
import pandas as pd
from pysnc import ServiceNowClient
from pysnc import GlideRecord
from pysnc import QueryCondition
import re
import hashlib
import time

from . import util
from .snc_auth import get_new_snc, get_new_snc_basic_auth, get_new_snc_args
from .submit_tables import SubmitTables
from .submit_table import SubmitTable
from .exceptions import MissingValueException, InvalidValueException, MissingDataException, SubmitException, SNCException

class BulkSubmitter:
    """
    The main class of SNulk responsible for loading formats and performing the bulk submission. Unless performing something complex,
    this should be the only class that needs referencing when using SNulk as a lib.
    """

    def __init__(self, submit_tables:SubmitTables = None, input_data:dict[Path,dict[str,pd.Dataframe]] = None,
                 process_sheets:dict[Path,set[str]] = None) -> None:
        """
        Initialize a BulkSubmitter object. The bulk submitter object is the main object for handling bulk submissions
        using SNulk.

        Args:
            submit_tables (SubmitTables, optional): A SubmitTables object which houses all the available table struct and table formats. Defaults to SubmitTables().
            input_data (dict[Path,dict[str,pd.Dataframe]], optional): The input data as dataframes organized by file_path->sheet_name->df. Defaults to None.
            process_sheets (dict[Path,set[str]], optional): The sheet_names of a file path that will be bulk submitted. Defaults to None.
        """
        self._submit_tables:SubmitTables = submit_tables if submit_tables is not None else SubmitTables()
        if input_data is None:
            input_data = {}
        if process_sheets is None:
            process_sheets = {}
        self._input_data:dict[Path,dict[str,pd.Dataframe]] = input_data
        self._process_sheets:dict[Path,set[str]] = process_sheets

    @property
    def submit_tables(self) -> SubmitTables:
        """
        Get the current SubmitTables object.

        Returns:
            SubmitTables: The current SubmitTables object.
        """
        return self._submit_tables

    @submit_tables.setter
    def submit_tables(self, value:SubmitTables) -> None:
        """
        Set the current SubmitTables object.

        Args:
            value (SubmitTables): The new SubmitTables object.
        """
        if value == None:
            value = SubmitTables()
        self._submit_tables = value

    def load_submit_tables_from_dir(self, dir_path:Path) -> None:
        """
        Loads the struct and format table yaml files from a given directory and sets the BulkSubmitter's
        SubmitTables object. Loading struct and format tables should be performed before any other operation
        in the BulkSubmitter. Any existing SubmitTables object will be overwritten.

        Args:
            dir_path (Path): A path to a directory containing the struct and format directories and subsequent yaml files.
        """
        if self._submit_tables is None:
            self._submit_tables = SubmitTables()
        self._submit_tables.load_dir(dir_path)

    def load_struct_submit_tables_from_file(self, file:Path) -> None:
        """
        Loads a struct object from a single struct yaml file.
        Note struct objects should be loaded before format objects.

        Args:
            file (Path): The yaml file to be loaded
        """
        if self._submit_tables is None:
            self._submit_tables = SubmitTables()
        self._submit_tables.load_struct_file(file)

    def load_format_submit_tables_from_file(self, file:Path) -> None:
        """
        Loads a format object from a single format yaml file.
        Note struct objects should be loaded before format objects.

        Args:
            file (Path): The yaml file to be loaded
        """
        if self._submit_tables is None:
            self._submit_tables = SubmitTables()
        self._submit_tables.load_format_file(file)

    def load_format_submit_tables_from_dir(self, dir_path:Path) -> None:
        """
        Loads the format objects from a directory containing format yaml files.
        Note struct objects should be loaded before format objects.

        Args:
            dir_path (Path): The directory to be loaded
        """
        if self._submit_tables is None:
            self._submit_tables = SubmitTables()
        self._submit_tables.load_format_dir(dir_path)

    def load_struct_submit_tables_from_dir(self, dir_path:Path) -> None:
        """
        Loads the format objects from a directory containing format yaml files.
        Note struct objects should be loaded before format objects.

        Args:
            dir_path (Path): The directory to be loaded
        """
        if self._submit_tables is None:
            self._submit_tables = SubmitTables()
        self._submit_tables.load_struct_dir(dir_path)

    def load_data_file(self, file:Path, excel_sheet_name:None|str|list[str]=None) -> None:
        """
        Loads an input data file into the input Dataframe list of BulkSubmitter. Existing Dataframes loaded from the same
        path will be overridden. All data in the given file will be loaded into Dataframes, however only those sheet names
        listed in 'excel_sheet_name' will be used for bulk submission. If no sheet names are listed in 'excel_sheet_name'
        then all sheets in the file will be used for bulk submission. Currently only xlsx files are supported.

        Args:
            file (Path): The input file path (.xlsx only)
            excel_sheet_name (None | str | list[str], optional): A list of sheet names from the given file to be used for bulk submission. Defaults to None.

        Raises:
            ValueError
        """
        if str(file.suffix).lower() == '.xlsx':
            # Read in all sheets as a dataframe
            temp: dict[str, pd.DataFrame] = util.input_from_excel(file, None)
            file = file.resolve()
            # Does not work because ints are converted to 4.0 etc
            #for df in temp.values():
            #    df.astype('string', copy=False)

            self._input_data[file] = temp

            if excel_sheet_name is None:
                self._process_sheets[file] = set(temp.keys())
            elif isinstance(excel_sheet_name, str):
                if not excel_sheet_name in temp.keys():
                    raise ValueError("Sheet name '" + excel_sheet_name + "' not found in '" + str(file) + "'")
                self._process_sheets[file] = {excel_sheet_name}
            elif isinstance(excel_sheet_name, list):
                self._process_sheets[file] = set()
                for sheet_name in excel_sheet_name:
                    if not str(sheet_name) in temp.keys():
                        raise ValueError("Sheet name '" + str(sheet_name) + "' not found in '" + str(file) + "'")
                    self._process_sheets[file].add(str(sheet_name))
            else:
                raise ValueError("The excel_sheet_name must be None, str, or list of str.")

        else:
            raise ValueError("Unsupported file type given as input file.")

    @staticmethod
    def _sub_helper(row, empty_is_none):
        def f(match) -> str:
            m: str = match.group(0)
            col_name: str = m[4:]
            col_name = col_name[:-4]
            if col_name in row and not pd.isna(row[col_name]) and (not empty_is_none or len(str(row[col_name])) != 0):
                logging.debug("Substituting '%s' for '%s'", str(m), str(row[col_name]))
                return str(row[col_name])
            else:
                raise MissingDataException("Column '" + str(col_name) + "' has no value in the current row and cannot be used for substitution.")
        return f

    @staticmethod
    def _bulk_submit_helper(row: pd.Series, submit_table: SubmitTable, snc: ServiceNowClient, dry_run: bool = False) -> pd.Series:
        try:
            logging.debug('Bulk submit processing row:\n%s', util.to_string(row.to_dict()))

            sysid_data_key = 'Submit SysId'
            for field in submit_table.return_fields:
                if field.name == "__SYSID__" and not field.data_key is None and isinstance(field.data_key, str) and len(field.data_key) != 0:
                    sysid_data_key: str = field.data_key

            if sysid_data_key in row and not pd.isna(row[sysid_data_key]) and len(str(row[sysid_data_key])) != 0:
                logging.debug('Skipping row because it has already been submitted.')
                return row

            gr: GlideRecord = snc.GlideRecord(submit_table.table_name)
            gr.initialize()

            hash_fields: dict[str, str] = {}
            to_hash: str = ""
            for field in submit_table.fields:
                logging.debug('Bulk submit handling field:\n%s', str(field))

                val = None
                if not field.data_key is None and field.data_key in row:
                    val = row[field.data_key]
                if (pd.isna(val) or (field.empty_is_none and len(str(val)) == 0)) and not field.default_value is None:
                    val: str = field.default_value
                if (pd.isna(val) or (field.empty_is_none and len(str(val)) == 0)) and field.append_hash:
                    val = " "

                if (pd.isna(val) or (field.empty_is_none and len(str(val)) == 0)):
                    if field.required:
                        raise MissingValueException("Unable to determine value for required field " + str(field.name) + " of table " + str(submit_table.table_name) + ".")
                    else:
                        logging.debug('Skipping field because no data:\n%s', str(field))
                        continue

                # TODO need a way to specify types when reading in columns so everything does not have to be a string # pylint: disable=fixme
                val = str(val)

                if field.substitution:
                    logging.debug("Performing substitution for:\n\n%s", val)
                    val = re.sub(r"(\[!--[^-]+--!\])", BulkSubmitter._sub_helper(row, field.empty_is_none), val)

                if not field.possible_values is None and not val in field.possible_values:
                    raise InvalidValueException("The value " + str(val) + " is not valid for field " + str(field.name) + ".")

                to_hash = to_hash + "---" + str(field.name) + ":" + str(val)

                if field.append_hash:
                    logging.debug("Append Hash - %s : %s", str(field.name), str(val))
                    hash_fields[field.name] = val
                else:
                    logging.debug("Set - %s : %s", str(field.name), str(val))
                    gr.set_value(field.name, val)

            sys_id: str | None = None
            if len(hash_fields) != 0:
                the_hash: str = hashlib.sha256(to_hash.encode()).hexdigest()

                logging.debug("Hashed data: %s", the_hash)

                gr_query: GlideRecord = snc.GlideRecord(submit_table.table_name)
                gr_query.limit = 1
                qc = None
                for k, v in hash_fields.items():
                    t: str = "Automated submission by BulkSubmitter - SHA256:" + the_hash
                    full_val = str(v)
                    if full_val == "" or full_val == " ":
                        full_val: str = t
                    else:
                        full_val = full_val + "\n\n" + t
                    if qc is None:
                        qc: QueryCondition = gr_query.add_query(str(k), "CONTAINS", t)
                    else:
                        qc.add_or_condition(str(k), "CONTAINS", t)
                    gr.set_value(k, full_val)
                logging.debug("Searching for existing record...")
                gr_query.query()
                logging.debug("Search finished")
                if gr_query.next():
                    logging.warning("Existing record found in %s that matches the submission.", str(submit_table.table_name))
                    logging.debug("\n%s", util.to_string_full(gr_query.serialize()))
                    iu: str = str(input("Would you like to continue? (Y/N)\n")).lower().strip()
                    if iu == "n":
                        logging.debug("Skipping submission of new record. The existing record will be used to fill in Submit SysId and other columns of the output.")
                        sys_id = gr_query.get_value('sys_id')
                        if sys_id is None or len(str(sys_id)) == 0:
                            raise SubmitException("Failed to get a valid SysId for the existing record of matching hash. Something is wrong.")
                        sys_id = str(sys_id)
                        gr = gr_query

            if sys_id is None:
                if dry_run:
                    logging.info("[DRY RUN] Row %s: insert skipped (dry-run mode)", str(row.to_dict()))
                    return row
                sys_id = gr.insert()
                if sys_id is None or len(str(sys_id)) == 0:
                    raise SubmitException("Failed to get a valid SysId for the submitted data of row. The submission may not have succeeded.")
                sys_id = str(sys_id)

            row[sysid_data_key] = sys_id

            for field in submit_table.return_fields:
                if field.name != "__SYSID__":
                    val = gr.get_value(field.name)
                    if val is None and field.none_is_empty:
                        val = ''
                    else:
                        val = str(val)
                    row[field.data_key] = val
        except Exception: # pylint: disable=broad-except
            logging.exception("Error while submitting row:\n%s", util.to_string(row.to_dict()))
        return row

    def _resolve_instance(self, short_name: str) -> tuple[str, SubmitTable]:
        """Resolve short_name to (instance_name, submit_table). Raises KeyError or ValueError on invalid input."""
        submit_table: SubmitTable = self._submit_tables.get_table_format(short_name)
        if submit_table is None:
            raise KeyError("A submit table format could not be found for the given short_name. - " + short_name)
        instance_name: str = submit_table.instance_name
        if instance_name is None or not isinstance(instance_name, str) or len(instance_name) == 0 or not re.fullmatch(r"[0-9a-zA-Z\-_]+", instance_name):
            raise ValueError("The 'instance name' must be a non-empty string containing only letters (case insensitive), numbers, '-', or '_'.")
        return instance_name, submit_table

    def bulk_submit(self, short_name: str, data: pd.DataFrame, snc: ServiceNowClient,
                    out_file: Path = None, excel_sheet_name: str = None,
                    confirm_first: bool = False, delay: float = 0.0, dry_run: bool = False) -> pd.DataFrame:
        """
        The main method of BulkSubmitter. This method will bulk submit a single dataframe based on the given format as pointed
        to by the short_name argument. The snc parameter is a ready-to-use ServiceNowClient. The default behavior
        of SNulk for recording Dataframe changes is to write the Dataframe back to its input file (including any other Dataframes that have not
        changed in order to preserve all unchanged data in the original file). The arguments out_file and excel_sheet_name
        are used to specify exactly what file and sheet a the data Dataframe came from.

        To override this default behavior, simply give a file
        path that was not loaded as input and this function will output data to that file path instead. Use excel_sheet_name to specify the
        sheet name for this new file. One can also use excel_sheet_name to change the output to a new sheet in the input file.

        Output is written once all rows in a Dataframe have been submitted. If an exception occurs during the submission of a row, the row
        will be skipped and an exception will be displayed. However, SNulk will attempt to submit the remaining rows. Any data that has changed
        should always be written to the output file unless a file system error occurs or an interrupt such as ctrl+c.

        Args:
            short_name (str): The name of the format that will be used to submit table data.
            data (pd.DataFrame): The data that will be used in the submission.
            snc (ServiceNowClient): An authenticated ServiceNowClient instance.
            out_file (Path, optional): The output file path that the dataframe will be written to. Defaults to None.
            excel_sheet_name (str, optional): The sheet name used for the dataframe in the output file path. Defaults to None.

        Raises:
            ValueError, TypeError, KeyError

        Returns:
            pd.DataFrame: The input Dataframe with any modifications made to it as a result of submission
        """
        if short_name is None or data is None:
            raise ValueError("short_name and data cannot be null.")
        if not isinstance(short_name, str) or not isinstance(data, pd.DataFrame):
            raise TypeError("short_name must be a string and data must be a pandas DataFrame.")
        if len(short_name) == 0 or len(data.index) == 0:
            raise ValueError("short_name and data must be non-empty.")

        _, submit_table = self._resolve_instance(short_name)

        table_name: str = submit_table.table_name
        if table_name is None or not isinstance(table_name, str) or len(table_name) == 0 or not re.fullmatch(r"[0-9a-zA-Z\-_]+", table_name):
            raise ValueError("The 'table name' must be a non-empty string containing only letters (case insensitive), numbers, '-', or '_'.")

        # Do this before submitting anything to try and avoid data loss if we can't write to file
        file_type = None
        if not out_file is None:
            out_file = util.test_file_writable(out_file)
            file_type: str = str(out_file.suffix).lower()
            if file_type != '.xlsx':
                raise ValueError("Unsupported file type given as output file.")

        results = []
        processed_indices = set()
        try:
            total_rows = len(data)
            for row_num, (idx, row) in enumerate(data.iterrows(), start=1):
                updated_row = BulkSubmitter._bulk_submit_helper(
                    row, submit_table, snc, dry_run=dry_run
                )
                results.append(updated_row)
                processed_indices.add(idx)

                # --confirm-first: after row 1, print return values and prompt
                if confirm_first and row_num == 1:
                    non_sysid_return_fields = [f for f in submit_table.return_fields if f.name != "__SYSID__"]
                    if dry_run:
                        print("  (no return fields \u2014 dry run mode)")
                    elif len(non_sysid_return_fields) == 0:
                        print("  (no return fields configured)")
                    else:
                        print("Return values for row 1:")
                        for field in non_sysid_return_fields:
                            val = updated_row.get(field.data_key, '')
                            print(f"  {field.data_key}: {val}")
                    print("Verify the record on your ServiceNow instance.")
                    remaining = total_rows - 1
                    response = str(input(f"Continue with remaining {remaining} rows? [y/N]: ")).strip()
                    if response.lower() not in ('y', 'yes'):
                        break
                    # if yes, continue loop

                # --delay: sleep after each row except the last; skip after row 1 when confirm_first active
                if delay > 0 and row_num < total_rows:
                    if confirm_first and row_num == 1:
                        pass  # user input already provided natural pause
                    else:
                        time.sleep(delay)
        except Exception: # pylint: disable=broad-except
            logging.exception("Unexpected exception while submiting dataframe: %s", str(short_name))
            
        remaining_rows = data.loc[~data.index.isin(processed_indices)]
        for _, remaining_row in remaining_rows.iterrows():
            results.append(remaining_row)

        ret = pd.DataFrame(results)

        if not dry_run:
            sysid_data_key = 'Submit SysId'
            for field in submit_table.return_fields:
                if field.name == "__SYSID__" and not field.data_key is None and isinstance(field.data_key, str) and len(field.data_key) != 0:
                    sysid_data_key: str = field.data_key

            for _, row in ret.iterrows():
                if not (sysid_data_key in row and not pd.isna(row[sysid_data_key]) and len(str(row[sysid_data_key])) != 0):
                    logging.warning("One or more submissions did not complete successfully. Check log for information.")
                    break

        if not dry_run and not out_file is None:
            logging.debug("Writing output to: %s",str(out_file))
            sn_to_df: dict[str, pd.Dataframe] = self._input_data.get(out_file)
            process_list: list[str] = []
            if sn_to_df is None:
                if out_file.exists():
                    logging.warning("Overwriting file %s without knowledge of original data may cause data loss.", str(out_file))
                    iu: str = str(input("Would you like to continue? (Y/N)\n")).lower().strip()
                    if iu == "n":
                        logging.debug("Output not written to %s by user choice.", str(out_file))
                        return ret
                # If sheet name is None then Sheet1 is used here
                if file_type == '.xlsx':
                    sn_to_df = util.output_to_excel(ret, out_file, excel_sheet_name, include_index=False)
                    process_list = list(sn_to_df.keys()) if not sn_to_df is None and len(sn_to_df.keys()) > 0 else [excel_sheet_name]
                else:
                    raise ValueError("Unsupported file type given as output file.")
            else:
                dfs: list[pd.DataFrame] = []
                sheet_names: list[str] = []
                found = False
                for k,v in sn_to_df.items():
                    if not excel_sheet_name is None and k == excel_sheet_name:
                        dfs.append(ret)
                        found = True
                        process_list.append(k)
                    else:
                        dfs.append(v)
                    sheet_names.append(k)
                if not found:
                    dfs.append(ret)
                    # If sheet name is None it will get a name SheetN where N is the number of sheets
                    sheet_names.append(excel_sheet_name)
                    process_list.append(excel_sheet_name)
                if file_type == '.xlsx':
                    sn_to_df = util.output_many_to_excel(dfs, out_file, sheet_names, None)
                else:
                    raise ValueError("Unsupported file type given as output file.")
            self._input_data[out_file] = sn_to_df
            if out_file not in self._process_sheets:
                self._process_sheets[out_file] = set()
            self._process_sheets[out_file].update(process_list)
            
        if dry_run:
            logging.info(ret.to_string())
            logging.info(ret.describe())

        return ret

    def bulk_submit_session(self, short_name: str, data: pd.DataFrame, creds: tuple = None, use_sso: bool = True,
                            use_hihop: bool = False, snc_args: dict = None, out_file: Path = None,
                            excel_sheet_name: str = None, confirm_first: bool = False,
                            delay: float = 0.0, dry_run: bool = False) -> pd.DataFrame:
        """
        A wrapper for the bulk_submit method that handles authentication to an instance by way of selenium and firefox. This method
        will open a firefox browser window to the ServiceNow instance, ask the user to manually login, and capture the login session before exiting.
        All other functionality should be the same as bulk_submit.

        Note you may need to navigate to /now/nav/ui/classic/params/target/ to get the browser session to close and SNulk to continue.

        Args:
            short_name (str): The name of the format that will be used to submit table data.
            data (pd.DataFrame): The data that will be used in the submission.
            creds (tuple, optional): A (username, password) tuple for automated login. Defaults to None.
            use_sso (bool, optional): If True treats login as SSO login. Defaults to True.
            use_hihop (bool, optional): If True authenticates through hihop. Defaults to False.
            snc_args (dict, optional): Additional arguments to initialize a ServiceNowClient object with. Defaults to None.
            out_file (Path, optional): The output file path that the dataframe will be written to. Defaults to None.
            excel_sheet_name (str, optional): The sheet name used for the dataframe in the output file path. Defaults to None.

        Raises:
            ValueError, TypeError, KeyError

        Returns:
            pd.DataFrame: The submitted dataframe with updated fields
        """
        if short_name is None or data is None:
            raise ValueError("short_name and data cannot be null.")
        if not isinstance(short_name, str) or not isinstance(data, pd.DataFrame):
            raise TypeError("short_name must be a string and data must be a pandas DataFrame.")
        if len(short_name) == 0 or len(data.index) == 0:
            raise ValueError("short_name and data must be non-empty.")

        instance_name, _ = self._resolve_instance(short_name)
        snc, msg = get_new_snc(instance_name, creds=creds, snc_args=snc_args, use_hihop=use_hihop, use_sso=use_sso)
        if msg is not None:
            raise SNCException(f"Failed to create ServiceNowClient: {msg}")
        return self.bulk_submit(short_name, data, snc, out_file, excel_sheet_name,
                                confirm_first=confirm_first, delay=delay, dry_run=dry_run)

    def bulk_submit_basicauth(self, short_name: str, data: pd.DataFrame, username: str,
                              password: str, snc_args: dict = None, out_file: Path = None,
                              excel_sheet_name: str = None, confirm_first: bool = False,
                              delay: float = 0.0, dry_run: bool = False) -> pd.DataFrame:
        """
        A wrapper for the bulk_submit method that handles authentication to an instance using basic auth via the provided username and password. All
        other functionality should be the same as bulk_submit.

        Args:
            short_name (str): The name of the format that will be used to submit table data.
            data (pd.DataFrame): The data that will be used in the submission.
            username (str): The username for basicauth.
            password (str): The password for basicauth.
            snc_args (dict): Additional arguments to initialize a ServiceNowClient object with. The auth arg will be supplied by this method.
            out_file (Path, optional): The output file path that the dataframe will be written to. Defaults to None.
            excel_sheet_name (str, optional): The sheet name used for the dataframe in the output file path. Defaults to None.

        Raises:
            ValueError, TypeError, KeyError

        Returns:
            pd.DataFrame: The submitted dataframe with updated fields
        """
        if short_name is None or data is None:
            raise ValueError("short_name and data cannot be null.")
        if not isinstance(short_name, str) or not isinstance(data, pd.DataFrame):
            raise TypeError("short_name must be a string and data must be a pandas DataFrame.")
        if len(short_name) == 0 or len(data.index) == 0:
            raise ValueError("short_name and data must be non-empty.")
        
        instance_name, _ = self._resolve_instance(short_name)
        snc = get_new_snc_basic_auth(instance_name, username=username, password=password, snc_args=snc_args)
        
        return self.bulk_submit(short_name, data, snc, out_file, excel_sheet_name,
                                confirm_first=confirm_first, delay=delay, dry_run=dry_run)

    def bulk_submit_all(self, short_name: str, username: str = None, password: str = None,
                        snc_args: dict = None, confirm_first: bool = False,
                        delay: float = 0.0, dry_run: bool = False) -> None:
        """
        This method uses bulk_submit to submit all input Dataframes according to the format indicated by the short_name. It will authenticate
        using basicauth if a username is given and no other authorization method is given. It will authenticate by session data obtained by
        manually logging in via firefox/selenium if no username is given.

        Args:
            short_name (str): The name of the format that will be used to submit table data.
            username (str): The username for basicauth. Defaults to None.
            password (str): The password for basicauth. Defaults to None.
            snc_args (dict, optional): Arguments to initialize a ServiceNowClient object. Defaults to None.
            confirm_first (bool): After row 1, prompt user to confirm before continuing. Defaults to False.
            delay (float): Seconds to sleep between row submissions. Defaults to 0.0.
            dry_run (bool): If True, skip gr.insert() calls. Defaults to False.
        """
        for file, sheet_names in self._process_sheets.items():
            sheet_names = list(sheet_names) # since we modify this list when processing it
            sn_to_df: dict[str, pd.DataFrame] = self._input_data[file]
            for sheet_name in sheet_names:
                if sheet_name in sn_to_df:
                    if username is None:
                        if snc_args is None or not ('auth' in snc_args or 'cert' in snc_args):
                            self.bulk_submit_session(short_name, sn_to_df[sheet_name], snc_args=snc_args, out_file=file, excel_sheet_name=sheet_name,
                                                     confirm_first=confirm_first, delay=delay, dry_run=dry_run)
                        else:
                            instance_name, _ = self._resolve_instance(short_name)
                            snc = get_new_snc_args(instance_name, snc_args)
                            self.bulk_submit(short_name, sn_to_df[sheet_name], snc, file, sheet_name,
                                            confirm_first=confirm_first, delay=delay, dry_run=dry_run)
                    else:
                        self.bulk_submit_basicauth(short_name, sn_to_df[sheet_name], username, password, snc_args, file, sheet_name,
                                                   confirm_first=confirm_first, delay=delay, dry_run=dry_run)
                else:
                    logging.warning("Sheet name '%s' not found in list of sheet names for '%s'. Skipping processing.", str(sheet_name), str(file))
