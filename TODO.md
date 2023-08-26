
- [x] Test how long it takes to deserialize grants from DB.
    - Is it worth it for storage backends to return raw data to speed up processes? 
    - Time against postgres how long to get 1000 grants
    - Time to convert those sql models to grants
    - If it's negligible, no need to create gate page raw etc
    - RESULTS:
        - with page size of 5000 - DB 0.20, conversion 0.06 ~25% of the time spent is converting grants
        - with page size of 1000 - DB 0.075, conversion 0.011 ~15% of the time spent is converting grants
        - with page size of 100 - DB 0.057, conversion 0.0012 ~2% of the time spent is converting grants
    - Should be split in storage backend
        - Need to return `RawGrantsPage` - raw data and next page token
        - another method to convert `RawGrantsPage` into `GrantsPage`
        - next page ref should always be stored as a string.  This way it's easily passed around. 

- [x] Change grant iterators to generators

- [ ] Speed up Multiprocess backend
    - avoid serializing all grants and passing to process
    - Should be able to tell subprocess page data and wait for new page data while the process goes
    - NEED TO CHECK if multiprocess.Event().is_set() takes a long time.
        - Is it okay to check for each grant
        - or should it just be every grant page

- [ ] Celery or Dramatiq style compute
    - Distributed compute
    - Send management task, wait for return - will give the best "async" performance as most of the time is waiting
    - management task will then kick off paging task
    - once new page token is available another paging task is kicked off until all are or cancel/found event is triggered
    - Get result
    - kick off cleanup task, don't wait
    - return result
