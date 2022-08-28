## Contributing
Thank you for considering contributing to Zigbee for Domoticz plugin. It is people like you that make it such a great and powerful tool.

You can contribute on different matters :

* Testing purpose
Contributors will help in the testing of the beta and pre-release.
You don't need to have specific known-how or knowledge, you'll have to run and test the code and report issues, gaps with docuentation ...

* End User Documentation
Contributors will help in developping/contributing to the plugin documentation, in order to improve the end user experience

* User Interface

We are looking for help on improving the User Interface. We have already a nice look and feel of our plugin Web interface, but there is room for further improvement and many on CSS side.

Technology to be used:
- html
- Javascript
- jquery
- css


* Plugin core
The plugin is written in Python3. The integration with Domoticz is done over the 'Python Plugin Framework' provided by domoticz.
You want to participate in the developement of the plugin, by either adding new Zigbee hardware devices, just contact us.


## Where do I go from here ?
If you've noticed a bug or have an enhancement request, or simply you took on issue from the GitHub Issue list, go ahead and propose your implementation.

### Fork & create a branch

If this is something you think you can fix, then [fork Domoticz-Zigate][] and
create a branch with a descriptive name. Make sure to select the right branch ( stable, beta )

A good branch name would be (where issue #325 is the ticket you're working on):

```sh
git checkout -b 325-add-chipolo-plug
```

### Did you find a bug?

* **Ensure the bug was not already reported** by [searching all issues][].

* If you're unable to find an open issue addressing the problem,
  [open a new one][new issue]. Be sure to include a **title and clear
  description**, as much relevant information as possible, and a **code sample**
  or an **test case** demonstrating the expected behavior that is not
  occurring.

* If possible, use the relevant bug report templates to create the issue.

### Implement your fix or feature

At this point, you're ready to make your changes! Feel free to ask for help;
everyone is a beginner at first :smile_cat:

### Make a Pull Request

At this point, you should switch back to your master branch and make sure it's
up to date with Domoticz-Zigate's stable/beta branch (stable or betat, depending where you start the fork) :

```sh
git remote add upstream <gitusername>@github.com:sasu-drooz/Domoticz-Zigate.git
git checkout stable
git pull upstream stable
```
Then update your feature branch from your local copy of stable, and push it!

```sh
git checkout 325-add-chipolo-plug
git rebase stable
git push --set-upstream origin 325-add-chipolo-plug
```

Finally, go to GitHub and [make a Pull Request][] :D

### Keeping your Pull Request updated

If a maintainer asks you to "rebase" your PR, they're saying that a lot of code
has changed, and that you need to update your branch so it's easier to merge.

To learn more about rebasing in Git, there are a lot of [good][git rebasing]
[resources][interactive rebase] but here's the suggested workflow:

```sh
git checkout 325-add-chipolo-plug
git pull --rebase upstream master
git push --force-with-lease 325-add-chipolo-plug
```
