# ju-cli
### JU is a cli-helper for devs hows working with mercurial and jira.

To use the script, you can activate virtualenv and then install the package:

```bash
$ hg clone https://your_server.com/dev_utils
$ cd dev_utils
$ pip install .
```

The you can run `ju --help` to see all available commands.

### Config
In `~/.jurc` you need to specify your jira auth data, mercurial auth data, aliases(optional).
> Note: repository http_basic in `.jurc` must be basic auth url.
> For example: `http_basic=https://login:password@server.com/repository`