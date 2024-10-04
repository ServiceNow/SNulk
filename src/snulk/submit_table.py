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

import logging
import re
from pathlib import Path
from ruamel.yaml import YAML

from . import util
from .exceptions import FormatException
from .submit_field import SubmitField
from .return_field import ReturnField

class SubmitTable:
    """
    A SubmitTable houses the description of a single table. The type of SubmitTable can be either a struct or format table. Struct SubmitTables
    store only structural information about a table on an instance while format tables describe exactly how to submit input data to a given
    table on an instance. If all struct tables are loaded first, all format table data should be a superset of one struct table.
    """
    
    def __init__(self, instance_name:str, table_name:str, short_name:str = None, fields:list[SubmitField] = None,
                 return_fields:list[ReturnField] = None) -> None:
        """
        Init method for a SubmitTable.

        Args:
            instance_name (str): The name of an instance.
            table_name (str): The name of a table on an instance.
            short_name (str, optional): The descriptive name of this format table or None if struct table.
            fields (list[SubmitField], optional): A non empty list of fields. Defaults to None.
            return_fields (list[ReturnField], optional): A non-empty list of return fields. Defaults to None.
        """
        self._short_name:str = short_name
        self._instance_name:str = instance_name
        self._table_name:str = table_name
        self._fields:dict[str, SubmitField] = None
        if not fields is None and isinstance(fields, list) and len(fields) != 0:
            fields.sort(key=lambda x: x.name)
            self._fields:dict[str, SubmitField] = {x.name: x for x in fields}
        self._return_fields:dict[str, ReturnField] = None
        if not return_fields is None and isinstance(return_fields, list) and len(return_fields) != 0:
            return_fields.sort(key=lambda x: x.name)
            self._return_fields:dict[str, ReturnField] = {x.name: x for x in return_fields}
            
    def __str__ (self) -> str:
        """
        The to string method that does a dump of this class to a json format.

        Returns:
            str: String representation of the class
        """
        self.sort()
        return util.pickle_json_string(self)
        
    def __eq__(self, other) -> bool:
        """
        Determines if two tables are equal by their instance and table name.
        """
        if not isinstance(other, SubmitTable):
            return False
        return (self._instance_name == other._instance_name and self._table_name == other._table_name)
    
    def __hash__(self) -> int:
        """
        Returns a hash of the instance and table name used for determining if two tables are equal.
        """
        i = 5
        i: int = i * 21 + hash(self._instance_name)
        i = i * 21 + hash(self._table_name)
        return i
    
    def copy(self) -> SubmitTable:
        """
        Performs a deep copy of the current SubmitTable object to produce a new SubmitTable object.

        Returns:
            SubmitTable: A new deep copy of the current SubmitTable
        """
        return self.__copy__()
    
    def __copy__(self) -> SubmitTable:
        new_fields = None
        if not self._fields is None:
            new_fields: list[SubmitField] = [v.copy() for v in self._fields.values()]
        new_return_fields = None
        if not self._return_fields is None:
            new_return_fields: list[SubmitField] = [v.copy() for v in self._return_fields.values()]
        return SubmitTable(self._instance_name, self._table_name, self._short_name, new_fields, new_return_fields)
        
    def __deepcopy__(self, memo) -> SubmitTable:
        if self in memo:
            return memo[self]
        ret: SubmitTable = self.__copy__()
        memo[self] = ret
        return ret
    
    def sort(self) -> None:
        """
        Sorts the object field dicts by their keys.
        """
        if not self._fields is None:
            for f in self._fields.values():
                f.sort()
            self._fields = {k: v for k, v in sorted(self._fields.items(), key=lambda item: item[0])}
        if not self._return_fields is None:
            self._return_fields = {k: v for k, v in sorted(self._return_fields.items(), key=lambda item: item[0])}
        
    @property
    def short_name(self) -> str:
        """
        Get short_name
        
        Returns:
            str: Current value
        """
        return self._short_name
    
    @short_name.setter
    def short_name(self, value:str) -> None:
        """
        Set short_name

        Args:
            value (str): new value
        """
        self._short_name = value
        
    @property
    def instance_name(self) -> str:
        """
        Get instance_name

        Returns:
            str: Current value
        """
        return self._instance_name
    
    @instance_name.setter
    def instance_name(self, value:str) -> None:
        """
        Set instance_name

        Args:
            value (str): new value
        """
        self._instance_name = value
        
    @property
    def table_name(self) -> str:
        """
        Get table_name

        Returns:
            str: Current value
        """
        return self._table_name
    
    @table_name.setter
    def table_name(self, value:str) -> None:
        """
        Set table_name

        Args:
            value (str): new value
        """
        self._table_name = value
        
    @property
    def fields(self) -> list[SubmitField]:
        """
        The the current fields. Will always return a list.

        Returns:
            list[SubmitField]: A list of SubmitFields. May be empty.
        """
        if self._fields is None:
            return list()
        ret = list(self._fields.values())
        ret.sort(key=lambda x: x.name)
        return ret
    
    @fields.setter
    def fields(self, value:list[SubmitField]) -> None:
        """
        Set the SubmitFields. Overrides any fields that already exists.
        The set list is sorted.

        Args:
            value (list[SubmitField]): A new list of SubmitFields
        """
        if not value is None and isinstance(value, list) and len(value) != 0:
            value.sort(key=lambda x: x.name)
            self._fields:dict[str, SubmitField] = {x.name: x for x in value}
        else:
            self._fields:dict[str, SubmitField] = None
        
    @property
    def return_fields(self) -> list[ReturnField]:
        """
        The the current fields. Will always return a list.

        Returns:
            list[ReturnField]: A list of ReturnFields. May be empty.
        """
        if self._return_fields is None:
            return list()
        ret = list(self._return_fields.values())
        ret.sort(key=lambda x: x.name)
        return ret
    
    @return_fields.setter
    def return_fields(self, value:list[ReturnField]) -> None:
        """
        Set the ReturnFields. Overrides any fields that already exists.
        The set list is sorted.

        Args:
            value (list[ReturnField]): A new list of ReturnFields
        """
        if not value is None and isinstance(value, list) and len(value) != 0:
            value.sort(key=lambda x: x.name)
            self._return_fields:dict[str, ReturnField] = {x.name: x for x in value}
        else:
            self._return_fields:dict[str, ReturnField] = None
        
    def add_or_merge_field(self, field:SubmitField, fmat:bool = False) -> None:
        """
        Adds a new SubmitField to this SubmitTable. If a SubmitField already exists, it will merge
        the current field with the new field. The new field will overwrite any conflicting data of the
        old field and add any that does not exist. This is used to combine struct table fields with
        format table fields.

        Args:
            field (SubmitField): The new submit field that is to be added.
            fmat (bool, optional): Indicates if what we are adding is a format field. Causes the method to produce warnings if a struct field did not already exist Defaults to False.
        """
        if not field is None and isinstance(field, SubmitField):
            if self._fields is None:
                if fmat:
                    logging.warning("Adding format for field that did not exist in table definition. - %s", field.name)
                self._fields = {field.name: field}
            elif len(self._fields) == 0:
                if fmat:
                    logging.warning("Adding format for field that did not exist in table definition. - %s", field.name)
                self._fields[field.name] = field
            elif field.name in self._fields:
                self._fields[field.name].merge(field)
            else:
                if fmat:
                    logging.warning("Adding format for field that did not exist in table definition. - %s", field.name)
                self._fields[field.name] = field
    
    def add_return_field(self, field:ReturnField) -> None:
        """
        Adds a new ReturnField to this SubmitTable. If a ReturnField already exists, the new field will completely 
        overwrite the old.

        Args:
            field (ReturnField): The new ReturnField
        """
        if not field is None and isinstance(field, ReturnField):
            if self._return_fields is None:
                self._return_fields = {field.name: field}
            elif len(self._return_fields) == 0:
                self._return_fields[field.name] = field
            elif field.name in self._return_fields:
                logging.warning("Return field already existed. Replaced with most recent. - %s", field.name)
                self._return_fields[field.name] = field
            else:
                self._return_fields[field.name] = field  
    
    @staticmethod 
    def load_from_file(file:Path, existing_tables:list[SubmitTable] = None, fmat:bool = False) -> list[SubmitTable]:
        """
        This loads a SubmitTable from a yaml file. The type of SubmitTable to be loaded is indicated by the fmat argument. 
        The existing_tables argument is a list of struct tables that have already been loaded. Tables in this list are
        copied and then merged with format tables of the same table and instance name. 

        Args:
            file (Path): The yaml file to load the SubmitTable from
            existing_tables (list[SubmitTable], optional): A list of already loaded struct tables if loading a format table. Defaults to None.
            fmat (bool, optional): If this is a format table or not. Defaults to False.

        Raises:
            FormatException: Describes issues when parsing the yaml file.

        Returns:
            list[SubmitTable]: All SubmitTables loaded from the yaml files
        """
        logging.debug("Loading table %s definitions from file: %s", ("format" if fmat else "structure" ), str(file))
        file = util.test_file_readable(file)
        ret: list[SubmitTable] = []
        with file.resolve().open() as f:
            yaml = YAML(typ='safe')
            yaml.default_flow_style = False
            for t in yaml.load_all(f):
                logging.debug("Loading SubmitTable:\n%s", util.to_string(t))
                if t is None or not isinstance(t, dict):
                    raise FormatException("Tried to load a table from a non-dictionary.")
                
                if not 'instance' in t or not util.validate_instance_name(t['instance']):
                    raise FormatException("The provided data must have a 'instance' that is a non-empty string containing a https:// url or only letters \
                                                 (case insensitive), numbers, '-', or '_'.")
                instance_name: str = util.get_instance_name(t['instance'])
                
                if not 'table' in t or t['table'] is None or not isinstance(t['table'], str) or len(t['table']) == 0 \
                        or not re.match(r"[0-9a-zA-Z\-_]+", t['table']):
                    raise FormatException("The provided data must have a 'table' that is a non-empty string containing only letters \
                                                 (case insensitive), numbers, '-', or '_'.")
                table_name: str = t['table']
                
                short_name = None
                if fmat:
                    if not 'short_name' in t or t['short_name'] is None or not isinstance(t['short_name'], str) or len(t['short_name']) == 0 \
                            or not re.match(r"[0-9a-zA-Z\-_]+", t['short_name']):
                        raise FormatException("The provided data must have a 'short_name' that is a non-empty string containing only letters \
                                                 (case insensitive), numbers, '-', or '_'.")
                    short_name: str = t['short_name']
                
                submittable = SubmitTable(instance_name, table_name, short_name)
                if not existing_tables is None and len(existing_tables) != 0:
                    existing_table: SubmitTable | None = next((arg for arg in existing_tables if arg == submittable), None)
                    if not existing_table is None:
                        submittable: SubmitTable = existing_table.copy()
                        # make sure to copy over any attributes of table formats not in table structs
                        if not short_name is None:
                            submittable.short_name = short_name
                ret.append(submittable)
                
                if 'fields' in t and not t['fields'] is None and isinstance(t['fields'], list) and len(t['fields']) != 0:
                    for f in t['fields']:
                        submittable.add_or_merge_field(SubmitField.load_from_dict(f, fmat), fmat)
                        
                if fmat and 'return_fields' in t and not t['return_fields'] is None and isinstance(t['return_fields'], list) and len(t['return_fields']) != 0:
                    for f in t['return_fields']:
                        rf: ReturnField = ReturnField.load_from_dict(f)
                        if not rf.name in submittable._fields and rf.name != '__SYSID__':
                            logging.warning("Adding format for return field that did not exist in table definition. - %s", rf.name)
                        submittable.add_return_field(rf)
                submittable.sort()
        return ret
