# TODO

- [ ] What would it take to add grant filters by tags? 
    - Matching just the key, or key/value pairs
    - Basically need to partition on every tag key and value to maintain performance
- [ ] optional function parameters and how to handle?


- [x] custom function i/o
- [x] JMESPath regex
    - instead of different functions just have a flag to do find or find all
    - **Solution** - Probably should just have a flag - `find_all` or `only_first` or `first_only` may be better because it says what it's going to do. 
        - This way there is only a `regex_find` and `regex_groups` function
        - This is super confusing now because it returns 5 different types
- [x] horizontal and vertical header table for locality matrix
- [x] locality and parallel paging after constructor or start.
    - After start just in case
- [x] What to name ComputeBackend and StorageBackend?
    - Engine - Already the Authzee engine - shouldn't reuse this
    - Component
    - Module - Like a space module - I like it
- [x] How to handle async enabled languages? 
    - Should all compute and storage be forced to async if available? 
    - Would it be better to have a flag set on the engines denoting if they are async? 
        - That would really complicate the code between all pieces trying to deal with sync vs async versions