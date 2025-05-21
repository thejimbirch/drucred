# Drucred

**Drucred** is a Python script for generating contributor credit reports from
issues on [Drupal.org](https://www.drupal.org). It fetches closed (fixed) issues
for a given project node ID and aggregates credit information into a Markdown
report and a CSV file.


## Features

- Fetches all "closed (fixed)" issues for a Drupal project.
- Extracts contributor credit from issue metadata.
- Counts contributions by individual and organization.
- Outputs:
  - A Markdown report with charts and sections.
  - A CSV file sorted by contribution count and organization.
- Uses local caching for efficiency.


## Installation

Clone the repository and ensure you have Python 3 installed.

```bash
git clone https://github.com/yourusername/drucred.git
cd drucred
pip install -r requirements.txt  # (if needed, e.g. for requests)
```


## Usage

`python drucred.py <project_node_id>`

For example, to fetch the issues from the Drupal CMS development repo, use:

`python drucred.py 3466967`

This will:

- Fetch and cache issue data in data/<project_machine_name>/
- Save reports in the output/ folder:
  - drucred_<project_machine_name>.md
  - drucred_<project_machine_name>.csv

### How to acquire the project's node ID

If you view source on and Drupal project, the shortlink reveals it:

`<link rel="shortlink" href="https://www.drupal.org/node/3466967" />`

If you are the maintainer on the project, you can also obtain the id from the
edit link on the project page:

`https://www.drupal.org/node/3283161/edit`


## Output Files

- output/drucred_<project>.md: Markdown file with credit summary and charts.
- output/drucred_<project>.csv: CSV file with username, organization, and
  contribution count.


## Respecting Drupal.org’s APIs

This tool uses [Drupal.org's REST API](https://www.drupal.org/drupalorg/docs/apis/rest-and-other-apis)

Please use it respectfully:

- Don't hammer the API with excessive requests.
- Caching is enabled by default to minimize load.
- The script includes a 1-second throttle between requests.

If you're building your own tooling against Drupal.org, we encourage you to read
their API documentation and follow best practices.


## Contributing

Feel free to open issues or submit pull requests to improve the script.
Contributions are welcome!


## License

This script is available under the GNU General Public License v3.0. See the
LICENSE file for details.

---

Made with :heart: on Cape Cod.
