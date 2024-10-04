# SNulk: ServiceNow Bulk Submit Tool for Table Records

SNulk provides a means to submit a large number of templated records to a table on a ServiceNow instance based on provided data. The table, instance, template, and data are all customizable and intended to be modified to fit the situation. A blog post illustrating how to use SNulk is coming soon. Check the [Security Research Blog Posts](https://securitylab.servicenow.com/research/) for updates.

## Setup

Below are instructions on how to setup and install SNulk and its dependencies.

### Install Dependencies

SNulk is a python CLI tool that uses [rye](https://rye.astral.sh/guide/installation/#installing-rye), [selenium](https://pypi.org/project/selenium/), and firefox. You will also likely need to install [geckodriver](https://github.com/mozilla/geckodriver/releases) so selenium can communicate with firefox. Note selenium, firefox, and geckodriver are only used to authenticate with an instance when not using basic auth credentials. If you plan to only use basic auth credentials for authentication then these dependencies are not required. 

Detailed instructions for installing the dependencies can be found on their website. Below are general commands on how one might install these dependencies for MacOS.

```bash
# Install rye
brew install rye
echo 'source "$HOME/.rye/env"' >> ~/.zprofile
echo 'source "$HOME/.rye/env"' >> ~/.zshrc

# Install firefox
brew install --cask firefox

# Install selenium (not needed if snulk is only being run inside the venv)
pip install selenium

# Install geckodriver
brew install geckodriver
```

### Install SNulk

We provide three ways to install and run SNulk: from PyPi, from source inside a virtual environment, and built and installed from source. The commands below detail these three install methods.

#### From PyPi (Recommended)

```bash
pip install SNulk
# See below for more cli command examples and options
snulk -h
# If you wish to uninstall snulk run this command
pip uninstall SNulk
```

#### From Source - In A Virtual Environment

```bash
git clone https://github.com/ServiceNow/SNulk.git
rye sync
# See below for more cli command examples and options
rye run snulk -h
```

#### From Source - Build And Install

```bash
git clone https://github.com/ServiceNow/SNulk.git
rye sync
rye build --clean
pip install --break-system-packages --user ./dist/snulk-*.whl
# See below for more cli command examples and options
python -m snulk -h
# If you wish to uninstall snulk run this command
pip uninstall snulk
```

## Running SNulk

SNulk can be used as both a CLI tool and as a python library by other tools. The examples below illustrate these two uses.

### SNulk CLI

The SNulk CLI is the easiest way to use SNulk. Below are some examples of how to use the CLI and full details of the CLI options. Note the input files mentioned are explained in a later section.

#### CLI Command Examples

The commands below assume SNulk was installed from PyPi. If SNulk was installed using a different method, replace `snulk` with either `rye run snulk` for the virtual environment or `python -m snulk` for the build from source method.

```bash
# Uses basic auth to authenticate to an instance
snulk -t submit_table -u user -p pass -n short_name -i data/file.xlsx > log.txt

# Uses selenium and firefox to manually login to and instance and grab the cookies
# You may need to manually navigate to /now/nav/ui/classic/params/target/ after login
snulk -t submit_table -n short_name -i data/file.xlsx > log.txt

# Only read submit data from sheet1 and sheet2 of file.xlsx
snulk -t submit_table -n short_name -i data/file.xlsx sheet1 sheet2 > log.txt
```

#### CLI Usage Instructions

```bash
usage: SNulk: ServiceNow Bulk Submit Tool for Table Records [-h] [--table_dir STD] [--format_table STD_FORMAT]
                                                            [--struct_table STD_STRUCT] [--username USERNAME]
                                                            [--password PASSWORD] --name SHORT_NAME --input INPUT
                                                            [INPUT ...] [--debug]

This tool provides a means to submit a large number of templated records to a table on a ServiceNow instance based on
provided data. The table, instance, template, and data are all customizable and intended to be modified to fit the
situation.

options:
  -h, --help                                       show this help message and exit
  --table_dir STD, -t STD                          The directory containing yaml files that define the structures of a
                                                   tables and the formats (templates) used to map input data to table
                                                   fields. The directory should contain two sub directories with the
                                                   names 'format' and 'struct' that house the associated yaml files.
                                                   This option can be given multiple times. If this option,
                                                   --format_table, or --struct_table is not given, SNulk will default
                                                   to using --table_dir '<cwd>/submit_table'.
  --format_table STD_FORMAT, -f STD_FORMAT         A path to either a format table yaml file or a directory containing
                                                   format table yaml files. This option can be given multiple files.
                                                   If this option, --table_dir, or --struct_table is not given, SNulk
                                                   will default to using --table_dir '<cwd>/submit_table'.
  --struct_table STD_STRUCT, -s STD_STRUCT         A path to either a struct table yaml file or a directory containing
                                                   struct table yaml files. This option can be given multiple files.
                                                   If this option, --table_dir, or --format_table is not given, SNulk
                                                   will default to using --table_dir '<cwd>/submit_table'.
  --username USERNAME, -u USERNAME                 The username to be used to login to an instance using basic auth.
                                                   If given then password must also be specified. If neither username
                                                   or password is given then authorization is conducted using the
                                                   session data obtained using selenium and firefox.
  --password PASSWORD, -p PASSWORD                 The password to be used to login to an instance using basic auth.
                                                   If given then username must also be specified. If neither username
                                                   or password is given the authorization is conducted using the
                                                   session data obtained using selenium and firefox.
  --name SHORT_NAME, -n SHORT_NAME                 The name of a format to be used when submitting data. This should
                                                   be the same as the 'short_name' value of one of the yaml files
                                                   provided as a format.
  --input INPUT [INPUT ...], -i INPUT [INPUT ...]  The input data. Currently only xlsx files are supported. The value
                                                   is a list where the first element is an xlsx file and the remaining
                                                   are sheet names in the file to be used when submitting data. For
                                                   example, '-i file.xlsx s1 s2 s3' will read from sheets s1, s2, and
                                                   s3 of file.xlsx when submitting records to the specified table. If
                                                   file.xlsx contained any additional sheets those sheets would be
                                                   ignored. If just '-i file.xlsx' is given then all sheets will be
                                                   used. The '-i' argument may be given multiple times to provide
                                                   multiple data sources.
  --debug, -d                                      Enable debug logging output.
```

### SNulk Library

SNulk can also be used as a library to provide further customization or use with other scripts. Below is a example on how to use SNulk as a library using the example data found under the `example` directory. This example illustrates multiple ways to perform the same task. Pick and choose what best fits your use case.

```python
from snulk import BulkSubmitter
from pathlib import Path

bs = BulkSubmitter()

# load the struct and format files
# make sure all struct files are loaded before format files
# load a single struct yaml file
bs.load_struct_submit_tables_from_file(Path("example/submit_table/struct/dev_incident.yaml"))
# load a single format yaml file
bs.load_format_submit_tables_from_file(Path("example/submit_table/format/test_submit.yaml"))
# load an entire directory of struct and format yaml files
bs.load_submit_tables_from_dir(Path("example/submit_table"))

# load input data
bs.load_data_file(Path("example/data/test_submit.xlsx"))
# submit input data using basic auth
bs.bulk_submit_all("test_incident", "username", "password")

# you can also use captured sessions to login
# you may need to navigate to '/now/nav/ui/classic/params/target/' manually
bs.bulk_submit_all("test_incident")

# it is also possible to use your own data frame for submission
bs.bulk_submit_basicauth("test_incident", data, "username", "password", Path("example/data/out.xlsx"), "Sheet_name")

# same as the previous example but using captured sessions to login
# you may need to navigate to '/now/nav/ui/classic/params/target/' manually
bs.bulk_submit_session("test_incident", data, Path("example/data/out.xlsx"), "Sheet_name")
```

## Input and Output Files

### Data Files

The required `--input` option takes as input a file and a list of sheet names. Currently, only xlsx files are supported. All xlsx files given are considered input sources for SNulk and will be used for submission. If sheet names are given, only the the sheet names listed for each file will be used for submission. Otherwise all sheets in a file will be used for submission. See the above help message for more information on the formatting and how to use the input option.

While only some input file sheet names may be used for submission, all input file sheets are loaded by Snulk. Snulk uses `pandas` to read and write input data. As such, all sheets of every file given as input are loaded as `Dataframes` and grouped by input file path and sheet name.

Any data that is requested to be retrieved after a successful submission is written back to the associated `Dataframe` from which the submission data was retrieved. Data is not written back to the originating file until all rows in a `Dataframe` have been submitted. If multiple `Dataframes` originate from the same file (i.e. the file had multiple sheets), all `Dataframes` will be written to the file on any given write. This is possible because all sheets have been loaded as `Dataframes` even if they are not being used. Upon some exception during the submission process of a `Dataframe`, any data successfully retrieved already and stored in the `Dataframe` is written back to its originating file before SNulk exits. This process for syncing `Dataframes` and files should preserve any unused sheets and data while ensuring any new data is recorded baring some problem with the file system itself. 

Note that any `Dataframe` used for submission will have at least one additional column added to it. This column stores the `sysid` of the submitted record. This allows SNulk to be run multiple times on the same input data and format file without duplicating submissions. That is if a `Dataframe` has a `sysid` already recorded for a given row, that row will be skipped with processing the `Dataframe`. The name of the column that stores the `sysid` of submitted records can be customized by specifying a **Format Return Field** with the special name `__SYSID__`. If a **Format Return Field** is not given with this special name then the column storing `sysid` defaults to the name `Submit SysId`. For more information on how to specify the data retrieved after a submission see the **Format Return Fields** section.

### Yaml Config Files

The required `--table_dir` option takes as input a directory that must contain the folders `format` and `struct`. These folders should contains the available **Format Yaml Files** and **Struct Yaml Files** respectively. The specification for these files is outlined below. All yaml files in these folders will be loaded and be available to SNulk for use regardless of what `--name` option is given. 

Note **Struct Yaml Files** are always loaded first to provide the basic structure of the available tables and fields to SNulk. **Format Yaml Files** are then loaded to provide SNulk specific information about what fields and data will actually be submitted for a specifically named (`short_name`) format. SNulk will produce warnings about fields and tables not defined in `struct` files but used in `format` files but will not stop processing. It will also warn about duplicate `struct` (same `instance` and `table` elements) or `format` (same `short_name`) files.

### Format Yaml Files

Below is an example of a format (template) yaml file that is used to map fields in the provided input data with the fields of a table on a specific instance.

```yml
---
short_name: name_of_this_format
instance: instance_name
table: table_name
return_fields:
  - name: __SYSID__
    data_key: new_field_name_in_data_1
    none_is_empty: true
  - name: number
    data_key: new_field_name_in_data_2
    none_is_empty: true
fields:
  - name: field_name_in_table
    data_key: field_name_in_data
    default_value: "A example default value '[!--some_field_in_data--!]'"
    required: true
    substitution: true
    append_hash: true
    empty_is_none: true
```

#### Format Header

Each format structure starts with a header that must contain the following entries.

```yml
short_name: name_of_this_format
instance: instance_name
table: table_name
return_fields:
fields:
```

##### short_name - (required) - (`[0-9a-zA-Z\-_]+`)

<sub>The name used to identify this format. This is what gets provided to the CLI under the option `--name`.</sub>

##### instance - (required) - (https url or `[0-9a-zA-Z\-_]+`)

<sub>The name of an instance (i.e. from `<instance-name>.service-now.com` or the full https url of an instance). This will be the instance that SNulk connects to in order to write data.</sub>

##### table_name - (required) - (`[0-9a-zA-Z\-_]+`)

<sub>The name of a table on the specified instance. This will be the table that is written to.</sub>

##### return_fields - (required) - (list containing 0 or more entries of type return_field)

<sub>This is a list that specifies the format options for return_fields. A return_field is a field of a table that SNulk retrieves after the new record has been submitted. Return fields map table data back into our input data to record information that gets generated server side once a record is created. This list can be empty but the entry for it must still be specified. For more information see **Format Return Fields** below.</sub>

##### fields - (required) - (list containing 1 or more entries of type field)

<sub>This is a list that specified the format options for fields. A field is a field of a table that SNulk includes when submitting a new record. Fields map input data to table data. This list cannot be empty. For more information see **Format Fields** below.</sub>

#### Format Return Fields

Each format structure can contain 0 or more return fields as specified below. These fields map data from the table back to our input data once a record has been submitted.

```yml
return_fields:
  - name: __SYSID__
    data_key: new_field_name_in_data_1
    none_is_empty: true
  - name: number
    data_key: new_field_name_in_data_2
    none_is_empty: true
```

##### name - (required) - (`[0-9a-zA-Z\-_]+`)

<sub>Name of a field in the table that SNulk will be reading data from once a record is submitted. To specify that the sysid of the submitted record should be retrieved, use the special name `__SYSID__` as shown above.</sub>

##### data_key - (required) - (`[0-9a-zA-Z\-_]+`)

<sub>The name of a field in the input data that SNulk will be writing data to once a record is submitted. The data is retrieved from field `name` of the table.</sub>

##### none_is_empty - (optional: default = `true`) - (`true/false`)

<sub>Indicates if `None`, `null`, or other data types that `pandas` considers null data (e.g. `NA`) should be written as an empty string when writing to the input data.</sub>

#### Format Fields

Format fields map the values of fields in input data to the fields of a ServiceNow table. The format field and its elements are outlined below.

Note the order of evaluation when determining a value for field `name` of the table record is: 1) `data_key`, 2) `default_value`. An element is determined to not be a valid value for field `name` if its value is a null value as determined by `pandas` or if `empty_is_none=true` and the elements value is an empty string. If no valid value is found an exception will be thrown unless `required=false`.

```yml
fields:
  - name: field_name_in_table
    data_key: field_name_in_data
    default_value: "A example default value '[!--some_field_in_data--!]'"
    required: true
    substitution: true
    append_hash: true
    empty_is_none: true
```

##### name - (required) - (`[0-9a-zA-Z\-_]+`)

<sub>Name of a field in the table that SNulk will be writing data to.</sub>

##### data_key - (optional: default = `None`) - (non-empty string)

<sub>The name of a field in the input data that SNulk will retrieve data from to write to field `name` in the table. This element of a format field does not need to be specified as data can also come from the `default_value` element.</sub>

##### default_value - (optional: default = `None`) - (non-empty string)

<sub>A non-empty string of some value that will be used as the value for field `name` if `data_key` is not given or if the row from input data have no value for `data_key`. This element of a format field does not need to be specified.</sub>

<sub>Note to specify a multi-line string in yaml use the format below:</sub>

```yml
fields:
  - name: engineering_details
    default_value: |
      line1
      line2
      line3
    required: true
```

##### required - (optional: default = `false`) - (true/false)

<sub>Specifies if a value for the field `name` must be determined before submitting a record to the table. If false, the field `name` will be omitted from the submitted record if no value can be determined. If true and no value can be determined, a exception will be thrown.</sub>

##### substitution - (optional: default = `false`) - (true/false)

<sub>Specifies if once a value for field `name` is determined, substitution should be performed. Substitution allows for the values of different fields of the same row from input data to be combined into a single value for submission to a table. The substitution signature is as follows `[!--input_field_name--!]`. Substitution can be used on the values retrieved from `data_key` or `default_value`. There can be multiple substitutions in the same string. Empty strings being none are controlled by the same `empty_is_none` false described below. This is if `empty_is_none=true` and the value for `input_field_name` of the input data is an empty string, it is treated as none. Attempting to substitute any null value, as determined by `pandas`, will raise an exception.</sub>

<sub>Example substitution in `default_value`:</sub>

```yml
fields:
  - name: engineering_details
    default_value: |
      Some text
      [!--input_field_name--!]
      Some more text [!--input_field_name_2--!]
    required: true
```

##### append_hash - (optional: default = `false`) - (true/false)

<sub>Once all the values for a new record are determined, SNulk will hash those values and append the hash to any field where `append_hash=true`. Before submission, SNulk will query the table to find any record whose field (i.e. the one with `append_hash`) contains the hash of the data about to be submitted. If an existing record exists, SNulk warns the user that a duplicate is about to be submitted and asks if they wish to continue. This is a means to prevent duplicate submissions.  The append value will be of the form `Automated submission by BulkSubmitter - SHA256:[hash]`. If you don't wish to have hashes appended or don't wish to perform this check, just remove any `append_hash` elements.</sub>

##### empty_is_none - (optional: default = `true`) - (true/false)

<sub>When set to true empty strings are treated as null values. That is, once a value is determined and it is an empty string, `empty_is_none=true` will cause the value to be treated as null. As null values as determined by `pandas` are errors, an exception will be raised. Note this element will also effect the behavior of substitution.</sub>

### Struct Yaml File

Below is an example of a struct (table structure) yaml file. These files are used to define the structure of fields in a table on a specific instance. Specifically, they allow the user to define available fields of a table and possible values for those fields. Currently this is used to alert the user when they are accessing a field not defined in a table or trying to assign a invalid value to a field. They can also be referenced by user to figure out what fields are available and what values are possible for those fields. The information is currently manually defined but future efforts will attempt to automate the building of these files. 

If a struct file is not defined for a given table and instance combination, it will produce warnings but not stop SNulk functionality. If you wish to get rid of the warnings simply define a struct file for a give table and instance combination and list the names of all the fields used in the associated format file.

```yml
---
instance: instance_name
table: table_name
fields:
  - name: field_name_in_table
  - name: field_name_in_table_2
    possible_values:
      - id: 'id1'
        short_description: 'Des1'
      - id: 'id2'
        short_description: 'des2'
      - id: 'id3'
        short_description: 'des3'
```

#### Struct Header

Each table structure starts with a header that must contain the following entries.

```yml
instance: instance_name
table: table_name
fields:
```

##### instance - (required) - (`https url or [0-9a-zA-Z\-_]+`)

<sub>The name of an instance (i.e. from `<instance-name>.service-now.com` or the full https url of an instance). This will be the instance the table is on. It should correspond to a table/instance pair in the format yaml files to be used.</sub>

##### table_name - (required) - (`[0-9a-zA-Z\-_]+`)

<sub>The name of a table on the specified instance. This will be the table from an instance. It should correspond to a table/instance pair in the format yaml files to be used.</sub>

##### fields - (required) - (list containing 1 or more entries of type field)

<sub>This is a list that specifies the available fields for a table on a given instance. This list cannot be empty. For more information see **Struct Fields** below.</sub>

#### Struct Fields

Struct fields are used to define the available fields for a table on an instance. The elements of struct fields are outlined below.

```yml
fields:
  - name: field_name_in_table
  - name: field_name_in_table_2
    possible_values:
      - id: 'id1'
        short_description: 'Des1'
      - id: 'id2'
        short_description: 'des2'
      - id: 'id3'
        short_description: 'des3'
```

##### name - (required) - (`[0-9a-zA-Z\-_]+`)

<sub>Name of a field on the table on an instance.</sub>

##### possible_values - (optional: default = `None`) - (list containing 1 or more entries of type field)

<sub>A list of possible values for the field with a given name. A possible value contains two elements: `id` and `short_description`. The `id` is the value that will actually be submitted to an instance while the `short_description` is a more human readable string that describes what the value means. Specifying the list of `possible_values` is not required but if specified the list must contain at leas one element.</sub>
