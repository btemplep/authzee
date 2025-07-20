# TODO

- [ ] What would it take to add grant filters by tags? 
    - Matching just the key, or key/value pairs
- [ ] custom function i/o
- [ ] horizontal and vertical header table for locality matrix

- [x] What to name ComputeBackend and StorageBackend?
    - Engine - Already the Authzee engine - shouldn't reuse this
    - Component
    - Module - Like a space module - I like it
- [x] How to handle async enabled languages? 
    - Should all compute and storage be forced to async if available? 
    - Would it be better to have a flag set on the engines denoting if they are async? 
        - That would really complicate the code between all pieces trying to deal with sync vs async versions