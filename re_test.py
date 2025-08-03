from typing import Any, Dict, List

import jmespath


def inner_join(lhs: List[Any], rhs: List[Any], expr: str) -> List[Dict[str, Any]]:
    result = []
    for l in lhs:
        for r in rhs:
            if jmespath.search( # how to pass the pointer from earlier?
                expr,
                {
                    "lhs": l,
                    "rhs": r
                }
            ) is True:
                result.append(
                    {
                        "lhs": l,
                        "rhs": r
                    }
                )
    
    return result



import re
from typing import List, Union


def regex_find(pattern: str, subject: Union[str, List[str]]) -> Union[None, str, List[Union[None, str]]]:
    if type(subject) is str:
        match = re.search(pattern, subject)
        if match is not None:
            return match.group()
        else:
            return None
    
    if type(subject) is list:
        result = []
        for sub in subject:
            match = re.search(pattern, sub)
            if match is not None:
                result.append(match.group())
            else:
                result.append(None)
    
    return result



import re
from typing import List, Union


def regex_find_all(pattern: str, subject: Union[str, List[str]]) -> Union[List[str], List[List[str]]]:
    if type(subject) is str:
        return re.findall(pattern, subject)
        
    if type(subject) is list:
        result = []
        for sub in subject:
            result.append(re.findall(pattern, sub))
    
    return result


def regex_groups(
    pattern: str, 
    subject: Union[str, List[str]]
) -> Union[
    None, 
    List[Union[None, str]], 
    List[
        Union[
            None, 
            List[
                Union[None, str]
            ]
        ]
    ]
]:
    if type(subject) is str:
        match = re.search(pattern, subject)
        if match is not None:
            return list(match.groups())
        else:
            return None
    
    if type(subject) is list:
        result = []
        for sub in subject:
            match = re.search(pattern, sub)
            if match is not None:
                result.append(list(match.groups()))
            else:
                result.append(None)
    
    return result


import re
from typing import List, Union


def regex_groups_all(pattern: str, subject: Union[str, List[str]]) -> Union[List[str], List[List[str]]]:
    if type(subject) is str:
        return [list(m.groups()) if m is not None else None for m in re.finditer(pattern, subject)]
        
    if type(subject) is list:
        result = []
        for sub in subject:
            result.append(
                [list(m.groups()) if m is not None else None for m in re.finditer(pattern, sub)]
            )
    
    return result

import json

results = [
    # inner_join(
    #     [
    #         {
    #             "l_field": "hello",
    #             "other_field": "thing"
    #         }
    #     ],
    #     [
    #         {
    #             "r_field": "goodbye",
    #             "r_other_field": "other thing"
    #         },
    #         {
    #             "r_field": "hello",
    #             "r_other_field": "other other thing"
    #         }
    #     ],
    #     "lhs.l_field == rhs.r_field"
    # ),
    # inner_join(
    #     [
    #         {
    #             "l_field": "hello",
    #             "other_field": "thing"
    #         }
    #     ],
    #     [
    #         {
    #             "r_field": "goodbye",
    #             "r_other_field": "other thing"
    #         }
    #     ],
    #     "lhs.l_field == rhs.r_field"
    # ),
    # regex_find("pattern.*", "some string here"),
    # regex_find("string.+", "some string here"),
    # regex_find("string.+", ["something", "here"]),
    # regex_find("string.+", ["something", "a string now", "here"]),
    # regex_find_all("pattern", "some string here"),
    # regex_find_all("string[0-9]", "some string3 here string4"),
    # regex_find_all("string.+", ["something", "here"]),
    # regex_find_all(
    #     "string[0-9]",
    #     [
    #         "something",
    #         "a string2 now string7 too",
    #         "here", 
    #         "another string3 here"
    #     ]
    # ),
    # regex_groups("pattern.*", "some string here"),
    # regex_groups("string.+", "some string here"),
    # regex_groups(
    #     "string (my_group[0-4])|string (my_other_group[5-9])", 
    #     "a string my_other_group9 another string my_group2"
    # ),
    # regex_groups("string.+", ["something", "here"]),
    # regex_groups("string.+", ["something", "a string now", "here"]),
    # regex_groups(
    #     "string (my_group[0-4])|string (my_other_group[5-9])", 
    #     [
    #         "something", 
    #         "a string my_other_group9 another string my_group2", 
    #         "here"
    #     ]
    # ),
    regex_groups_all("pattern.*", "some string here"),
    regex_groups_all("string.+", "some string here"),
    regex_groups_all(
        "string (my_group[0-4])|string (my_other_group[5-9])", 
        "a string my_other_group9 another string my_group2"
    ),
    regex_groups_all("string.+", ["something", "here"]),
    regex_groups_all("string.+", ["something", "a string now", "here"]),
    regex_groups_all(
        "string (my_group[0-4])|string (my_other_group[5-9])", 
        [
            "something", 
            "a string my_other_group9 another string my_group2", 
            "here"
        ]
    )
]


for res in results:
    print(
        json.dumps(
            res,
            indent=4
        )
    )

