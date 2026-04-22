# 🚀 Guide: Uploading "Air Canvas" to GitHub

Follow these steps to host your project on GitHub so you can share it or include the link in your college submission.

---

### Phase 1: Local Preparation
You already have Git initialized, so we just need to save your current progress.

1.  **Stage your files**:
    ```bash
    git add .
    ```
2.  **Create your first commit**:
    ```bash
    git commit -m "Initial commit: Air Canvas Pro Suite with Kalman Filter and Undo"
    ```

---

### Phase 2: Create a Repository on GitHub
1.  Go to **[GitHub.com](https://github.com)** and log in.
2.  Click the **"+"** icon in the top-right corner and select **"New repository"**.
3.  **Repository name**: `Air-Canvas` (or your chosen name).
4.  **Public/Private**: Select "Public" if you want to share the link.
5.  **Initialize**: Do **NOT** check "Add a README", "Add .gitignore", or "Choose a license" (we already have those files).
6.  Click **"Create repository"**.

---

### Phase 3: Connecting & Pushing
On the page that appears after creating the repo, look for the section **"…or push an existing repository from the command line"**. 

Run these commands in your terminal (replace `<YOUR_GITHUB_URL>` with the one shown on your screen):

1.  **Rename the branch to main** (modern standard):
    ```bash
    git branch -M main
    ```
2.  **Add the remote origin**:
    ```bash
    git remote add origin <YOUR_GITHUB_URL>
    ```
    *(It will look like `https://github.com/YourUsername/Air-Canvas.git`)*
3.  **Push the code**:
    ```bash
    git push -u origin main
    ```

---

### ✅ Success!
Your project is now live. Refresh your GitHub page to see your files and your beautiful README.

**Tip:** Put the link to your GitHub repository in your project synopsis and presentation slides. It shows great software engineering practice!
