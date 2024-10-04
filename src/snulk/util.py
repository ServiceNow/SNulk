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

import os
import pprint
import io
from pathlib import Path
import re
import jsonpickle
import pandas as pd

from .exceptions import InstanceNameFormatException, FilePathException

def pickle_json_string(obj) -> str:
    return jsonpickle.encode(obj, unpicklable=True, indent=2, keys=True)

def json_string(obj) -> str:
    return jsonpickle.encode(obj, unpicklable=False, indent=2, keys=True)

def test_file_writable(output:Path) -> Path:
    output = output.resolve()
    if output.exists():
        if not (output.is_file() and os.access(str(output), os.W_OK)):
            raise FilePathException('Error: Unable to write to output \'' + output + '\'. The path is not a file or is not writable.')
    else:
        if output.parent.exists():
            if not (output.parent.is_dir() and os.access(str(output.parent), os.W_OK)):
                raise FilePathException('Error: Unable to write to output \'' + output + '\'. The parent path is not a directory or is not writable.')
        else:
            raise FilePathException('Error: Unable to write to output \'' + output + '\'. The parent path is missing.')
    return output

def test_file_readable(input_path:Path) -> Path:
    input_path = test_file_readable_no_throw(input_path)
    if input_path is None:
        raise FilePathException('Unable to access input file \'' + str(input_path) + '\'.')
    return input_path

def test_file_readable_no_throw(input_path:Path) -> Path:
    input_path = input_path.resolve()
    if not (input_path.exists() and input_path.is_file() and os.access(str(input_path), os.R_OK)):
        return None
    return input_path

def test_dir_readable(input_path:Path) -> Path:
    input_path = input_path.resolve()
    if not (input_path.exists() and input_path.is_dir() and os.access(str(input_path), os.R_OK) and os.access(str(input_path), os.W_OK)):
        raise FilePathException('Unable to access input dir \'' + str(input_path) + '\'.')
    return input_path

def to_string(obj) -> str:
    stream = io.StringIO()
    pprint.pprint(obj,stream=stream, depth=3, sort_dicts=False, indent=2, width=1000)
    return stream.getvalue()

def to_string_full(obj) -> str:
    stream = io.StringIO()
    pprint.pprint(obj,stream=stream, indent=2, width=1000, sort_dicts=False)
    return stream.getvalue()
    
def input_from_excel(input_path:Path, excel_sheet_name:None|str|list[str]=None) -> dict[str, pd.DataFrame]:
    input_path = test_file_readable(input_path)
    
    if not (excel_sheet_name is None or isinstance(excel_sheet_name, str) or isinstance(excel_sheet_name, list)):
        raise ValueError("The sheet_name must be None, a string, or a list or strings.")
    if isinstance(excel_sheet_name, list):
        for s in excel_sheet_name:
            if not isinstance(s, str):
                raise ValueError("The list of sheet_names must only contain strings.")
    
    # TODO need a way to specify what type the columns are # pylint: disable=fixme
    data: dict[str, pd.DataFrame] | pd.DataFrame = pd.read_excel(input_path, engine='openpyxl', sheet_name=excel_sheet_name, dtype=str)
    # None -> all: dict, list of 1 or more -> select: dict, str -> dataframe
    # return should be a dict of sheet_name to dataframe
    if isinstance(data, dict):
        return data
    # only time it is not a dict is when a string was given
    return {excel_sheet_name: data}

def output_to_excel(df:pd.DataFrame, output_path:Path, sheet_name:str=None, include_index:bool=False) -> dict[str, pd.DataFrame]:
    return output_many_to_excel([df], output_path, [sheet_name], [include_index])

def output_many_to_excel(dfs:list[pd.DataFrame], output_path:Path, sheet_names:list[str]=None, include_indexes:list[bool]=None) -> dict[str, pd.DataFrame]:
    pairs:list[(pd.DataFrame,str,bool)] = []
    ret:dict[str, pd.DataFrame] = {}
    
    for i in range(len(dfs)):
        sheet_name = "Sheet" + str(i+1)
        if not (sheet_names is None or len(sheet_names) == 0 or i >= len(sheet_names) or sheet_names[i] is None or 
                (not isinstance(sheet_names[i], str)) or len(sheet_names[i]) == 0):
            sheet_name = sheet_names[i]
        include_index = False
        if not (include_indexes is None or len(include_indexes) == 0 or i >= len(include_indexes) or include_indexes[i] is None or 
                (not isinstance(include_indexes[i], bool))):
            include_index = include_indexes[i]
        pairs.append((dfs[i], sheet_name, include_index))
        ret[sheet_name] = dfs[i]

    output_path = output_path.resolve()
    parent_dir = output_path.parent
    parent_dir.mkdir(parents=True, exist_ok=True)
    
    with pd.ExcelWriter(str(output_path), engine="xlsxwriter", date_format='YYYY-MM-DD', datetime_format='YYYY-MM-DD', 
                        engine_kwargs={'options': {'strings_to_urls': False}}) as writer:
        
        for pair in pairs:
            pair[0].to_excel(writer, sheet_name=pair[1], startrow=1, header=False, index=pair[2])
            # Add header and create table
            instances_worksheet = writer.sheets[pair[1]]
            # Get the dimensions of the dataframe
            (input_df_max_row, input_df_max_col) = pair[0].shape
            # Create a list of column headers, to use in add_table()
            column_settings = [{'header': column} for column in pair[0].columns]
            # Add the Excel table structure. Pandas will add the data
            instances_worksheet.add_table(0, 0, input_df_max_row, input_df_max_col - 1, {'columns': column_settings})
            # Make the columns wider for clarity.
            instances_worksheet.set_column(0, input_df_max_col - 1, 12)
    
    return ret

def validate_instance_name(instance: str) -> bool:
    if instance is None or not isinstance(instance, str) or len(instance) == 0:
        return False
    elif '://' in instance:
        instance = instance.rstrip('/')
        if not instance.startswith('https://'):
            return False
        return True
    elif re.match(r"[0-9a-zA-Z\-_]+", instance):
        return True
    return False

def get_instance_name(instance: str) -> bool:
    if instance is None or not isinstance(instance, str) or len(instance) == 0:
        raise InstanceNameFormatException("The instance name must be a non-empty string.")
    elif '://' in instance:
        instance = instance.rstrip('/')
        if not instance.startswith('https://'):
            raise InstanceNameFormatException("Must provide https:// url")
        return instance
    elif re.match(r"[0-9a-zA-Z\-_]+", instance):
        return 'https://%s.service-now.com' % instance
    raise InstanceNameFormatException("Invalid instance name. Only https:// urls and non-empty strings containing only letters \
                                        (case insensitive), numbers, '-', or '_' are supported.")
