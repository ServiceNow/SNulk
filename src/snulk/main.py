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

import sys
import argparse
import logging
from pathlib import Path

from . import util
from .bulk_submitter import BulkSubmitter

def main() -> None:
    script_dir: Path = Path.cwd().resolve()
    formatter = lambda prog: argparse.HelpFormatter(prog,max_help_position=52)
    parser = argparse.ArgumentParser(description="This tool provides a means to submit a large number of \
        templated records to a table on a ServiceNow instance based on provided data. The table, instance, \
        template, and data are all customizable and intended to be modified to fit the situation.", 
        prog='SNulk: ServiceNow Bulk Submit Tool for Table Records',formatter_class=formatter)
    
    parser.add_argument("--table_dir", "-t", action='append', required=False, dest="std", 
                        help="The directory containing yaml files that define the structures of a tables and the formats (templates) used to map input data \
                            to table fields. The directory should contain two sub directories with the names 'format' and 'struct' that house the associated \
                            yaml files. This option can be given multiple times. If this option, --format_table, or --struct_table is not given, SNulk will \
                            default to using --table_dir '<cwd>/submit_table'.")
    parser.add_argument("--format_table", "-f", action='append', required=False, dest="std_format", help="A path to either a format table yaml file or a directory \
        containing format table yaml files. This option can be given multiple files. If this option, --table_dir, or --struct_table is not given, SNulk will \
        default to using --table_dir '<cwd>/submit_table'.")
    parser.add_argument("--struct_table", "-s", action='append', required=False, dest="std_struct", help="A path to either a struct table yaml file or a directory \
        containing struct table yaml files. This option can be given multiple files. If this option, --table_dir, or --format_table is not given, SNulk will \
        default to using --table_dir '<cwd>/submit_table'.")
    parser.add_argument("--username", "-u", action='store', required=False, dest="username", default=None, help="The username to be used to login to an instance \
        using basic auth. If given then password must also be specified. If neither username or password is given then authorization is conducted using the \
        session data obtained using selenium and firefox.")
    parser.add_argument("--password", "-p", action='store', required=False, dest="password", default=None, help="The password to be used to login to an instance \
        using basic auth. If given then username must also be specified. If neither username or password is given the authorization is conducted using the \
        session data obtained using selenium and firefox.")
    parser.add_argument("--name", "-n", action='store', required=True, dest="short_name", help="The name of a format to be used when submitting data. This should \
        be the same as the 'short_name' value of one of the yaml files provided as a format.")
    # Each -i is treated as a separate list
    # First arg is the file path and the remaining args are the sheet names
    parser.add_argument('--input', "-i", action='append', required=True, nargs='+', dest="input", help="The input data. Currently only xlsx files are supported. \
        The value is a list where the first element is an xlsx file and the remaining are sheet names in the file to be used when submitting data. For example, \
            '-i file.xlsx s1 s2 s3' will read from sheets s1, s2, and s3 of file.xlsx when submitting records to the specified table. If file.xlsx contained any \
            additional sheets those sheets would be ignored. If just '-i file.xlsx' is given then all sheets will be used. The '-i' argument may be given multiple \
            times to provide multiple data sources.")
    parser.add_argument('--debug', '-d', action='store_true', required=False, dest="debug", help="Enable debug logging output.")
    
    args: argparse.Namespace = parser.parse_args()
    
    loglevel: int = logging.WARNING
    if args.debug:
        loglevel = logging.DEBUG
    logging.basicConfig(level=loglevel, format="[%(asctime)s][%(levelname)s] - %(message)s", datefmt='%y-%m-%d %H:%M:%S', 
                        handlers=[logging.StreamHandler(sys.stdout)])
    
    username: str = args.username
    password: str = args.password
    short_name: str = args.short_name
    if short_name is None:
        raise ValueError("name cannot be null.")
    if not isinstance(short_name, str):
        raise TypeError("name must be a string.")
    if len(short_name) == 0:
        raise ValueError("name must be non-empty.")
    
    if (username is None or password is None) and not (username is None and password is None):
        raise ValueError("username and password cannot be null if one is provided.")
    
    table_format_paths: list[Path] = []
    table_struct_paths: list[Path] = []
    
    if not args.std_format is None and len(args.std_format) != 0:
        for elm in args.std_format:
            table_format_paths.append(Path(elm).resolve())
    if not args.std_struct is None and len(args.std_struct) != 0:
        for elm in args.std_struct:
            table_struct_paths.append(Path(elm).resolve())
    if not args.std is None and len(args.std) != 0:
        for elm in args.std:
            table_format_paths.append(Path(elm).joinpath('format').resolve())
            table_struct_paths.append(Path(elm).joinpath('struct').resolve())
            
    if (args.std_format is None or len(args.std_format) == 0) and (args.std_struct is None or len(args.std_struct) == 0) and (args.std is None or len(args.std) == 0):
        default_input_path: Path = script_dir.joinpath("..", "submit_table").resolve()
        table_format_paths.append(default_input_path.joinpath('format').resolve())
        table_struct_paths.append(default_input_path.joinpath('struct').resolve())
        
    bs = BulkSubmitter()
    
    for tsp in table_struct_paths:    
        if tsp.is_dir():
            tsp: Path = util.test_dir_readable(tsp)
            bs.load_struct_submit_tables_from_dir(tsp)
        else:
            tsp: Path = util.test_file_readable(tsp)
            bs.load_struct_submit_tables_from_file(tsp)
    
    for tfp in table_format_paths:
        if tfp.is_dir():
            tfp: Path = util.test_dir_readable(tfp)
            bs.load_format_submit_tables_from_dir(tfp)
        else:
            tfp: Path = util.test_dir_readable(tfp)
            bs.load_format_submit_tables_from_file(tfp)
    
    inputt: list[list[str]] = args.input
    parsed_input: dict[Path, list[str]] = {}
    for lis in inputt:
        file = Path(lis[0])
        file: Path = util.test_file_readable(file)
        if len(lis) == 1:
            parsed_input[file] = None
        elif len(lis) == 2:
            parsed_input[file] = str(lis[1])
        else:
            elms: list[str] = []
            first = True
            for elm in lis:
                if first:
                    first = False
                else:
                    elms.append(str(elm))
            parsed_input[file] = elms
            
    for k,v in parsed_input.items():
        bs.load_data_file(k, v)
    bs.bulk_submit_all(short_name, username, password)

if __name__ == '__main__':
    sys.exit(main())