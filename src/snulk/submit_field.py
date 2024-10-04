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

from . import util
from .exceptions import FormatException

class SubmitField:
    """
    A SubmitField houses the description of a single field in a table. The type of SubmitField can be either a struct or format field. Struct
    SubmitFields store only structural information about a field in a table on an instance while format fields describe exactly how to submit
    input data to a given table on an instance for a specific field. If all struct fields are loaded first, all format field data should be a
    superset of one format field.
    """
    
    def __init__(self, name:str, possible_values:dict[str, str] = None, data_key:str = None, 
                 required:bool = False, default_value:str = None, empty_is_none:bool = True,
                 append_hash:bool = False, substitution:bool = False) -> None:
        """
        Init for a SubmitField

        Args:
            name (str): The name of the field in the table on the instance that data will be written to.
            possible_values (dict[str, str], optional): _description_. Defaults to None.
            data_key (str, optional): The name of the column in the input data that data will be read from or None if using default_value. Defaults to None.
            required (bool, optional): If this field needs to be written when submitting a record. Enables checks for empty data. Defaults to False.
            default_value (str, optional): A default value for the field in the event data_key is none. Defaults to None.
            empty_is_none (bool, optional): Treat empty strings as null values. Defaults to True.
            append_hash (bool, optional): Append a SHA256 hash of all submitted data to this field and use it to check for already submitted records. Defaults to False.
            substitution (bool, optional): Enable substitution checks in the value that is to be submitted for this field. Defaults to False.
        """
        self._name:str = name
        self._possible_values:dict[str, str] = possible_values
        self._data_key:str = data_key
        self._required:bool = required
        self._default_value:str = default_value
        self._empty_is_none:bool = empty_is_none
        self._append_hash:bool = append_hash
        self._substitution:bool = substitution
        
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
        Determines if return fields are equal by the name.
        """
        if not isinstance(other, SubmitField):
            return False
        return (self._name == other._name)
    
    def __hash__(self) -> int:
        """
        Returns a hash of the name used for determining if two tables are equal.
        """
        i = 5
        i: int = i * 21 + hash(self._name)
        return i
    
    def copy(self) -> SubmitField:
        """
        Performs a deep copy of the current SubmitField object to produce a new SubmitField object.

        Returns:
            SubmitField: A new deep copy of the current SubmitField
        """
        return self.__copy__()
    
    def __copy__(self) -> SubmitField:
        ret = SubmitField(self._name, None if self._possible_values is None else self._possible_values.copy(), 
                          self._data_key, self._required, self._default_value, self._empty_is_none, self._append_hash,
                          self._substitution)
        ret.sort()
        return ret
        
    def __deepcopy__(self, memo) -> SubmitField:
        if self in memo:
            return memo[self]
        ret: SubmitField = self.__copy__()
        memo[self] = ret
        return ret
    
    def sort(self) -> None:
        """
        Sorts the object field dicts by their keys.
        """
        if not self._possible_values is None:
            self._possible_values = {k: v for k, v in sorted(self._possible_values.items(), key=lambda item: item[0])}
    
    def merge(self, other:SubmitField) -> None:
        """
        Merges an existing SubmitField with another SubmitField. Any values in the current SubmitField are overwritten
        by those in the other SubmitField unless the value is empty.

        Args:
            other (SubmitField): The SubmitField to merge the current SubmitField with.
        """
        if not other is None and isinstance(other, SubmitField):
            for attr, value in vars(self).items():
                if attr in other.__dict__ and (value is None or (not value is None and not other.__dict__[attr] is None)):
                    self.__dict__[attr] = other.__dict__[attr]
                    
    @property
    def name(self) -> str:
        """
        Get name
        
        Returns:
            str: Current value
        """
        return self._name
    
    @name.setter
    def name(self, value:str) -> None:
        """
        Set name

        Args:
            value (str): new value
        """
        self._name = value
        
    @property
    def data_key(self) -> str:
        """
        Get data_key
        
        Returns:
            str: Current value
        """
        return self._data_key
    
    @data_key.setter
    def data_key(self, value:str) -> None:
        """
        Set data_key

        Args:
            value (str): new value
        """
        self._data_key = value
        
    @property
    def default_value(self) -> str:
        """
        Get default_value
        
        Returns:
            str: Current value
        """
        return self._default_value
    
    @default_value.setter
    def default_value(self, value:str) -> None:
        """
        Set default_value

        Args:
            value (str): new value
        """
        self._default_value = value
        
    @property
    def required(self) -> bool:
        """
        Get required
        
        Returns:
            bool: Current value
        """
        return self._required
    
    @required.setter
    def required(self, value:bool) -> None:
        """
        Set required

        Args:
            value (bool): new value
        """
        self._required = value
        
    @property
    def possible_values(self) -> dict[str, str]:
        """
        Get possible_values

        Returns:
            dict[str, str]: The dict of possible_values or None if empty.
        """
        return self._possible_values
    
    @possible_values.setter
    def possible_values(self, value:dict[str, str]) -> None:
        """
        Set possible_values

        Args:
            value (dict[str, str]): new value
        """
        self._possible_values = value
        
    @property
    def empty_is_none(self) -> bool:
        """
        Get empty_is_none
        
        Returns:
            bool: Current value
        """
        return self._empty_is_none
    
    @empty_is_none.setter
    def empty_is_none(self, value:bool) -> None:
        """
        Set empty_is_none

        Args:
            value (bool): new value
        """
        self._empty_is_none = value
        
    @property
    def append_hash(self) -> bool:
        """
        Get append_hash
        
        Returns:
            bool: Current value
        """
        return self._append_hash
    
    @append_hash.setter
    def append_hash(self, value:bool) -> None:
        """
        Set append_hash

        Args:
            value (bool): new value
        """
        self._append_hash = value
        
    @property
    def substitution(self) -> bool:
        """
        Get substitution
        
        Returns:
            bool: Current value
        """
        return self._substitution
    
    @substitution.setter
    def substitution(self, value:bool) -> None:
        """
        Set substitution

        Args:
            value (bool): new value
        """
        self._substitution = value
        
    @staticmethod
    def load_from_dict(struct:dict, fmat:bool = False) -> SubmitField:
        """
        Loads a SubmitField from a portion of a yaml file. The type of SubmitField to be loaded is indicated by the fmat argument.

        Args:
            struct (dict): The portion of a yaml file that describes a SubmitField.
            fmat (bool, optional): If this is a format table field or not. Defaults to False.

        Raises:
            FormatException: Describes issues when parsing the yaml file.

        Returns:
            SubmitField: A new SubmitField.
        """
        logging.debug("Loading SubmitField:\n%s", util.to_string(struct))
        if struct is None or not isinstance(struct, dict):
            raise FormatException("Tried to load a field from a non-dictionary.")
        if not 'name' in struct or struct['name'] is None or not isinstance(struct['name'], str) or len(struct['name']) == 0 \
                or not re.match(r"[0-9a-zA-Z\-_]+", struct['name']):
            raise FormatException("The provided field data must have a 'name' that is a non-empty string containing only letters \
                                        (case insensitive), numbers, '-', or '_'.")
        name: str = struct['name']
        
        if fmat:
            data_key = None
            if 'data_key' in struct and not struct['data_key'] is None and isinstance(struct['data_key'], str) and len(struct['data_key']) != 0:
                data_key: str = struct['data_key']
            default_value = None
            if 'default_value' in struct and not struct['default_value'] is None and isinstance(struct['default_value'], str):
                default_value: str = struct['default_value']
            required = False
            if 'required' in struct and not struct['required'] is None and isinstance(struct['required'], bool):
                required: bool = struct['required']
            empty_is_none = True
            if 'empty_is_none' in struct and not struct['empty_is_none'] is None and isinstance(struct['empty_is_none'], bool):
                empty_is_none: bool = struct['empty_is_none']
            append_hash = False
            if 'append_hash' in struct and not struct['append_hash'] is None and isinstance(struct['append_hash'], bool):
                append_hash: bool = struct['append_hash']
            substitution = False
            if 'substitution' in struct and not struct['substitution'] is None and isinstance(struct['substitution'], bool):
                substitution: bool = struct['substitution']
            return SubmitField(name, None, data_key, required, default_value, empty_is_none, append_hash, substitution)
        else:
            possible_values = None
            if 'possible_values' in struct and not struct['possible_values'] is None and isinstance(struct['possible_values'], list) and len(struct['possible_values']) != 0:
                for pv in struct['possible_values']:
                    logging.debug("Loading Possible Value:\n%s", util.to_string(pv))
                    if pv is None or not isinstance(struct, dict):
                        raise FormatException("Tried to load a possible value from a non-dictionary.")
                    if not 'id' in pv or pv['id'] is None or not isinstance(pv['id'], str) or len(pv['id']) == 0:
                        raise FormatException("The provided possible value must have a 'id' that is a non-empty string containing.")
                    idd: str = pv['id']
                    short_description = None
                    if 'short_description' in pv and not pv['short_description'] is None and isinstance(pv['short_description'], str) and len(pv['short_description']) != 0:
                        short_description: str = pv['short_description']
                    if possible_values is None:
                        possible_values: dict[str, str] = {}
                    possible_values[idd] = short_description
            return SubmitField(name, possible_values)