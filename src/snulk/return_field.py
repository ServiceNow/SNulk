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

class ReturnField:
    """
    Describes how to write data back to our input data sources after a record has been submitted.
    """
    
    def __init__(self, name:str, data_key:str, none_is_empty:bool = True) -> None:
        """
        Init for a ReturnField

        Args:
            name (str): The name of the field in the table on the instance that data will be returned from.
            data_key (str): The name of the column in the input data that returned data from field name will be written to.
            none_is_empty (bool, optional): If null returned values should be treated as empty strings. Defaults to True.
        """
        self._name:str = name
        self._data_key:str = data_key
        self._none_is_empty:bool = none_is_empty
        
    def __str__ (self) -> str:
        """
        The to string method that does a dump of this class to a json format.

        Returns:
            str: String representation of the class
        """
        return util.pickle_json_string(self)
        
    def __eq__(self, other) -> bool:
        """
        Determines if return fields are equal by the name and data key.
        """
        if not isinstance(other, ReturnField):
            return False
        return (self._name == other._name and self._data_key == other._data_key)
    
    def __hash__(self) -> int:
        """
        Returns a hash of the name and data key used for determining if two tables are equal.
        """
        i = 5
        i: int = i * 21 + hash(self._name)
        i = i * 21 + hash(self._data_key)
        return i
    
    def copy(self) -> ReturnField:
        """
        Performs a deep copy of the current ReturnField object to produce a new ReturnField object.

        Returns:
            ReturnField: A new deep copy of the current ReturnField
        """
        return self.__copy__()
    
    def __copy__(self) -> ReturnField:
        ret = ReturnField(self._name, self._data_key, self._none_is_empty)
        return ret
        
    def __deepcopy__(self, memo) -> ReturnField:
        if self in memo:
            return memo[self]
        ret: ReturnField = self.__copy__()
        memo[self] = ret
        return ret

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
    def none_is_empty(self) -> bool:
        """
        Get none_is_empty
        
        Returns:
            bool: Current value
        """
        return self._none_is_empty
    
    @none_is_empty.setter
    def none_is_empty(self, value:bool) -> None:
        """
        Set none_is_empty

        Args:
            value (bool): new value
        """
        self._none_is_empty = value

    @staticmethod
    def load_from_dict(struct:dict) -> ReturnField:
        """
        Loads a ReturnField from a portion of a yaml file.

        Args:
            struct (dict): The portion of a yaml file that describes a ReturnField.

        Raises:
            FormatException: Describes issues when parsing the yaml file.

        Returns:
            ReturnField: A new ReturnField.
        """
        logging.debug("Loading ReturnField:\n%s", util.to_string(struct))
        
        if struct is None or not isinstance(struct, dict):
            raise FormatException("Tried to load a field from a non-dictionary.")
        
        if not 'name' in struct or struct['name'] is None or not isinstance(struct['name'], str) or len(struct['name']) == 0 \
                or not re.match(r"[0-9a-zA-Z\-_]+", struct['name']):
            raise FormatException("The provided field data must have a 'name' that is a non-empty string containing only letters \
                                        (case insensitive), numbers, '-', or '_'.")
        name: str = struct['name']
        
        if not 'data_key' in struct or struct['data_key'] is None or not isinstance(struct['data_key'], str) or len(struct['data_key']) == 0:
            raise FormatException("The provided field data must have a 'name' that is a non-empty string")
        data_key: str = struct['data_key']
        
        none_is_empty = True
        if 'none_is_empty' in struct and not struct['none_is_empty'] is None and isinstance(struct['none_is_empty'], bool):
            none_is_empty: bool = struct['none_is_empty']
        
        return ReturnField(name, data_key, none_is_empty)