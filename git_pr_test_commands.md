[Test out a Pull Request branch before merging]

1. Fetch the PR branch from remote:
```sh
git fetch origin feature/tkinter-dark-theme-10734679094469100824
```
_Fetches the latest code for the PR branch from the remote repository._

2. Check out the PR branch locally:
```sh
git checkout feature/tkinter-dark-theme-10734679094469100824
```
_Switches your working directory to the PR branch so you can test it._

3. (Optional) Pull the latest changes for the branch:
```sh
git pull origin feature/tkinter-dark-theme-10734679094469100824
```
_Ensures your local branch is up to date with the remote._

4. Run your tests or review the changes as needed.

[If you want to merge the PR after testing:]

1. Switch to the target branch (e.g., main or develop):
```sh
git checkout main
```
_Switches to the branch you want to merge into._

2. Pull the latest changes:
```sh
git pull origin main
```
_Ensures your target branch is up to date._

3. Merge the PR branch:
```sh
git merge feature/tkinter-dark-theme-10734679094469100824
```
_Merges the PR branch into your target branch locally._

4. Push the merged changes to remote:
```sh
git push origin main
```
_Updates the remote repository with the merged changes._

[If you do NOT want to keep the PR changes:]

1. Switch back to your original branch (e.g., main):
```sh
git checkout main
```
_Returns to your main branch._

2. Delete the local PR branch (optional):
```sh
git branch -D feature/tkinter-dark-theme-10734679094469100824
```
_Removes the local copy of the PR branch._

Your local copy is now reverted to the state before testing the PR branch.
