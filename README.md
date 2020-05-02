# Environment Setup

## Load the submodule

Run the following command to pull the dataset submodule.

~~~
git submodule update --init
~~~

After the command, you should check the `dataset` folder and make sure you see
the topology zoo dataset.

## Install dependencies

Use `pip3` to install the python dependencies.

~~~
pip3 install --user flask
pip3 install --user networkx
pip3 install --user lark-parser
~~~

## Run the frontend

Run the following command in the root of the project:

~~~
$ python3 demo.py
~~~

Then you can access the demo page through [this url](https://localhost:5000/demo.html).
