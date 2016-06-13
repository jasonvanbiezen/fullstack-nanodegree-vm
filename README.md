#[Fullstack Nanodegree Projects]

Udacity Fullstack Nanodegree Projects.
By: [Jason van Biezen](https://github.com/jasonvanbiezen)

## Contents

- [Requirements](#requirements)
- [Tournament Database Project](#tournament_database_project)
- [Item Catalog Project](#item_catalog_project)
- [License](#license)

## Requirements

1. Python 2.7
2. PostgreSQL (Not required if using vagrant)
3. Vagrant
4. VirtualBox (Or other virtual PC)

## Tournament Database Project

Swiss Tournament Database Sceme and Python methods and test driver.  Instructions below for launching tests in a vagrant session.

1. From repository root, navigate to vagrant directory.
2. Start vagrant: # vagrant up
3. SSH into vagrant session: # vagrant ssh
4. Navigation to the tounament project directory /vagrant/tournament
5. Project includes database file tournament.sql, tournament methods in tournament.py, and unit test file tournament_test.py
6. Run tests by executing the test file: # python tournament_test.py

## Item Catalog Project

Item Catalog Database Project with User Authentication and Public/Private Catalogs of items, organized by category.  Please read below for installation instructions.  

1. From repository root, navigate to vagrant directory.
2. Start vagrant
 * # vagrant up
3. SSH into vagrant session
 * # vagrant ssh
4. Navigation to the catalog project directory /vagrant/catalog.
5. Google and Facebook oauth APIs will require client IDs and secrets.  The application looks for these in the following environment variables.
 1. Google Client ID: CATALOG_DB_GCLIENT_ID
 2. The Google Client must have an authorized redirect URI and Javascript origin of 'http://localhost:5000/'
 3. Google Client Secret: CATALOG_DB_GSECRET_KEY
 4. Facebook Client ID: CATALOG_DB_FBCLIENT_ID
 5. Facebook Client Secret: CATALOG_DB_FBCLIENT_KEY
6. If launching for the first time, run database_setup.py
 * # python database_setup.py
7. Launch the web application
 * # python application.py

## License

Code in this repository is licensed under [GPLv2](https://www.gnu.org/licenses/old-licenses/gpl-2.0.en.html).  If you use my code in your project, or find it useful, I only ask that you add my name and a link to my github repo.  However, using this code directly in your Udacity project will constitute a violation of the code of conduct you agreed to when taking your course; please use my code for reference purposes only in this case.

