# Contribution Guidelines for Simple Chest Shop

Thank you for your interest in contributing to Simple Chest Shop! We welcome contributions from developers of all backgrounds to help us create the best possible chest shop plugin for Minecraft.

These guidelines outline the process and best practices for contributing to this project. By participating, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md) (Coming soon!).

## Getting Started

1.  **Fork the Repository:** Create your own fork of the Simple Chest Shop repository on GitHub.

2.  **Clone Your Fork:** Clone your forked repository to your local machine:

    ```bash
    git clone https://github.com/YOUR_USERNAME/SimpleChestShop.git
    cd SimpleChestShop
    ```

3.  **Set Up Your Development Environment:**
    *   Ensure you have a suitable development environment set up for PySpigot development. This includes:
        *   Java Development Kit (JDK) - Required by Spigot.
        *   Minecraft Server (Paper recommended) with PySpigot, Geyser, TownyAdvanced, VaultUnlocked, PlaceholderAPI and LuckPerms installed.
        *   A text editor or IDE for code editing (VS Code, Sublime Text, etc.).

4.  **Create a Branch:** Before making any changes, create a new branch for your contribution:

    ```bash
    git checkout -b feature/your-new-feature
    # OR
    git checkout -b bugfix/fix-that-pesky-bug
    ```

## Contribution Types

We welcome various types of contributions:

*   **Bug Fixes:** Addressing existing issues and improving stability.
*   **New Features:** Implementing new functionalities and enhancements.
*   **Code Improvements:** Refactoring, optimizing, and improving code quality.
*   **Documentation:** Enhancing the README, creating tutorials, and improving documentation.
*   **Testing:** Writing unit tests and testing the plugin on different server environments.
*   **Accessibility Improvements:** Ensuring the plugin is accessible to all players, especially those with disabilities.

## Coding Standards

*   **Jython 2.7 Compatibility:** Ensure your code is compatible with Jython 2.7, as that is what PySpigot currently uses. Do NOT use Python 3 features.
*   **Code Style:** Follow the PEP 8 style guide for Python code. Use a linter (like `flake8`) to help maintain consistent code style.
*   **Comments:** Add clear and concise comments to explain your code, especially for complex logic.
*   **Error Handling:** Implement robust error handling to prevent crashes and provide informative error messages.
*   **Plugin Dependencies:**  Be mindful of dependencies (TownyAdvanced, VaultUnlocked, LuckPerms, etc.) and handle cases where these plugins might not be present.
*   **Configuration:** If you add new features, provide configurable options in the `config.yml` file to allow server owners to customize the plugin's behavior.

## Submitting a Pull Request

1.  **Commit Your Changes:** Commit your changes with clear and descriptive commit messages.

    ```bash
    git add .
    git commit -m "feat: Add a new feature"
    ```

2.  **Push to Your Fork:** Push your changes to your forked repository:

    ```bash
    git push origin feature/your-new-feature
    ```

3.  **Create a Pull Request:** Create a pull request from your branch to the `main` branch of the Simple Chest Shop repository.

4.  **Pull Request Description:**
    *   Provide a clear and detailed description of your changes in the pull request.
    *   Explain the problem your changes are solving or the feature you are adding.
    *   Include any relevant information or context that reviewers should be aware of.

## Review Process

*   Your pull request will be reviewed by one or more maintainers of the project.
*   We may ask you to make revisions or provide additional information.
*   Be responsive to feedback and address any concerns raised during the review process.
*   Once your pull request is approved, it will be merged into the `main` branch.

## Reporting Issues

If you encounter any bugs, issues, or have suggestions for improvements, please open an issue on the GitHub repository. Provide as much detail as possible, including:

*   Minecraft server version
*   PySpigot version
*   Simple Chest Shop version
*   Steps to reproduce the issue
*   Error messages (if any)
*   Relevant configuration settings

## Code of Conduct

Please be respectful and considerate of others when contributing to this project. We are committed to creating a welcoming and inclusive environment for all contributors.

Thank you again for your contributions! We look forward to working with you to make Simple Chest Shop even better.
