
import re
from typing import Dict, List, Union


from jmespath import exceptions, functions


class CustomFunctions(functions.Functions):
    """JMESPath custom functions.

    Along with standard `Built-in JMESPath Functions<https://jmespath.org/specification.html#built-in-functions>`_
    the following custom functions are added.

    - ``pyregex(expression: str, string: str) -> Union[str, None]`` 
        
        - Uses python's built-in ``re.fullmatch`` on the given ``string`` with the regex ``expression``
        
        - Returns the string if a full match is found or else None.

    - ``pyregex_group(expression: str, string: str, group: int) -> Union[str, None]``

        - Uses python's built-in ``re.fullmatch`` on the given set of ``strings`` with the regex ``expression``

        - Then pulls the given regex ``group`` number from the expression

        - Returns the matching regex group if found, or else None.
    
    - ``lower(string: str) -> str``
        
        - Convert string to lowercase.
    
    - ``upper(string: str) -> str``
        
        - Convert string to uppercase.

    There is also a self regulating regex cache that is added to this class.
    Because of this, **instances of this class are not thread safe** . 
    
    Parameters
    ----------
    regex_cache_size : int, optional
        Max number of compiled regex patterns to cache, by default 10000
    """

    def __init__(self, regex_cache_size: int = 10000):
        super().__init__()
        self._regex_cache_size = regex_cache_size
        self._regex_cache_count = 0
        self._regex_cache: Dict[str, re.Pattern]= {}

    
    def _get_regex(self, expression: str) -> re.Pattern:
        if expression not in self._regex_cache:
            self._regex_cache[expression] = re.compile(expression)
            self._regex_cache_count += 1
            if self._regex_cache_count > self._regex_cache_size:
                # if cache is full, remove the oldest entries
                for _ in range(self._regex_cache_count - self._regex_cache_size):
                    self._regex_cache.pop(next(iter(self._regex_cache)))
                    self._regex_cache_count -= 1
        
        return self._regex_cache[expression]


    @functions.signature(
        {"types": ["string"]}, 
        {"types": ["string"]}
    )
    def _func_pyregex(self, expression: str, string: str) -> Union[str, None]:
        if self._get_regex(expression).fullmatch(string) is not None:
            return string
        
        return None
    
    
    @functions.signature(
        {"types": ["string"]}, 
        {"types": ["string"]}, 
        {"types": ["number"]}
    )
    def _func_pyregex_group(
        self, 
        expression: str, 
        string: str, 
        group: int
    ) -> Union[str, None]:
        if type(group) != int:
            raise exceptions.JMESPathError(
                "In function pyregex_group, type of 'group' was {} but the input must translate to an integer.".format(type(group))
            )

        if group < 1:
            raise exceptions.JMESPathError("In function pyregex_group, value of 'group' was {} but the input must be greater than 0.")

        group_match = None
        re_match = self._get_regex(expression).fullmatch(string)
        if re_match is not None:
            re_groups = re_match.groups()
            if group <= len(re_groups):
                group_match = re_groups[group - 1]

        return group_match


    @functions.signature(
        {"types": ["string"]}
    )
    def _func_lower(self, string: str) -> str:
        return string.lower()


    @functions.signature(
        {"types": ["string"]}
    )
    def _func_upper(self, string: str) -> str:
        return string.upper()
