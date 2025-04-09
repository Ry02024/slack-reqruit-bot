# Project Title

This project is designed to analyze and post job recruitment information to Slack. It consists of several components that work together to achieve this functionality.

## Project Structure

```
project-name
├── .github
│   └── workflows
│       └── ci.yml                # CI/CD configuration for GitHub Actions
├── data
│   └── reqruit.txt               # Text file containing job recruitment information
├── src
│   ├── __init__.py               # Empty file for package initialization
│   ├── gemini_slack_poster.py    # Contains the GeminiSlackPoster class for posting to Slack
│   ├── company_recruit_analysis.py # Contains the CompanyRecruitAnalysis class for analyzing job data
│   └── main.py                   # Entry point for the application
├── requirements.txt              # List of required packages
└── README.md                     # Project documentation
```

## Components

- **GeminiSlackPoster**: A class responsible for posting job recruitment information to Slack. It includes methods to format and send messages to a specified Slack channel.

- **CompanyRecruitAnalysis**: A class that analyzes the job recruitment data. It provides methods to extract insights and statistics from the recruitment information.

- **Main Entry Point**: The `main.py` file serves as the entry point for the application, orchestrating the flow of data and invoking the necessary classes and methods.

## Data

The project uses a text file located in the `data` directory, `reqruit.txt`, which contains the job recruitment information that will be analyzed and posted.

## Requirements

The `requirements.txt` file lists all the necessary packages that need to be installed for the project to run successfully.

## CI/CD

The project includes a GitHub Actions configuration file located in the `.github/workflows` directory, which automates the CI/CD process.

## Installation

To set up the project, clone the repository and install the required packages:

```bash
pip install -r requirements.txt
```

## Usage

To run the application, execute the `main.py` file:

```bash
python src/main.py
```

## License

This project is licensed under the MIT License.