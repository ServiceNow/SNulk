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

from . import util
from .submit_table import SubmitTable

class SubmitTables:
    """
    SubmitTables houses the lists of table structs and table formats for use with BulkSubmitter. It provides some methods
    for loading and setting these table structures.
    """
    
    def __init__(self) -> None:
        """
        Init method for the SubmitTables.
        """
        self._table_structs:dict[str, SubmitTable] = {}
        self._table_formats:dict[str, SubmitTable] = {}
        
    def __str__ (self) -> str:
        """
        The to string method that does a dump of this class to a json format.

        Returns:
            str: String representation of the class
        """
        self.sort()
        return util.pickle_json_string(self)
    
    def sort(self) -> None:
        """
        Sorts the object field dicts by their keys.
        """
        self._table_structs = {k: v for k, v in sorted(self._table_structs.items(), key=lambda item: item[0])}
        self._table_formats = {k: v for k, v in sorted(self._table_formats.items(), key=lambda item: item[0])}
        
    def get_table_format(self, short_name:str) -> SubmitTable:
        """
        Retrieves the table format based on its name.

        Args:
            short_name (str): The name of a format for a table.

        Returns:
            SubmitTable: The table format for the given name or None.
        """
        if short_name in self._table_formats:
            return self._table_formats[short_name]
        return None
        
    def load_dir(self, dir_path:Path) -> None:
        """
        Loads table struct and format objects from the given directory which should contain struct and 
        format sub-directories and struct/format yaml files. Note struct objects should be loaded before
        format objects.

        Args:
            dir_path (Path): The directory to be loaded
        """
        dir_path = util.test_dir_readable(dir_path)
        struct_dir: Path = util.test_dir_readable(dir_path.joinpath('struct'))
        format_dir: Path = util.test_dir_readable(dir_path.joinpath('format'))
        self.load_struct_dir(struct_dir)
        self.load_format_dir(format_dir)
        
    def load_struct_dir(self, dir_path:Path) -> None:
        """
        Loads the struct objects from a directory containing struct yaml files. 
        Note struct objects should be loaded before format objects.

        Args:
            dir_path (Path): The directory to be loaded
        """
        logging.debug("Loading struct dir: %s", str(dir_path))
        dir_path = util.test_dir_readable(dir_path)
        for child in dir_path.iterdir():
            child: Path = util.test_file_readable_no_throw(child)
            if not child is None:
                self.load_struct_file(child)
        
    def load_struct_file(self, file:Path) -> None:
        """
        Loads a struct object from a single struct yaml file.
        Note struct objects should be loaded before format objects.

        Args:
            file (Path): The yaml file to be loaded
        """
        new_tables: list[SubmitTable] = SubmitTable.load_from_file(file, None, False)
        for nt in new_tables:
            if nt.instance_name + "_" + nt.table_name in self._table_structs:
                logging.warning("Duplicate struct definition found a table. Using the latest definition. " 
                                + nt.instance_name + " - " + nt.table_name)
            self._table_structs[nt.instance_name + "_" + nt.table_name] = nt
            
    def load_format_dir(self, dir_path:Path) -> None:
        """
        Loads the format objects from a directory containing format yaml files. 
        Note struct objects should be loaded before format objects.

        Args:
            dir_path (Path): The directory to be loaded
        """
        logging.debug("Loading format dir: %s", str(dir_path))
        dir_path = util.test_dir_readable(dir_path)
        for child in dir_path.iterdir():
            child: Path = util.test_file_readable_no_throw(child)
            if not child is None:
                self.load_format_file(child)
    
    def load_format_file(self, file:Path) -> None:
        """
        Loads a format object from a single format yaml file.
        Note struct objects should be loaded before format objects.

        Args:
            file (Path): The yaml file to be loaded
        """
        new_tables: list[SubmitTable] = SubmitTable.load_from_file(file, list(self._table_structs.values()), True)
        for nt in new_tables:
            if nt.short_name in self._table_formats:
                logging.warning("Duplicate format definition found a table. Using the latest definition. %s", nt.short_name)
            self._table_formats[nt.short_name] = nt
