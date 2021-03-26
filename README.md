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
pip3 install --user pydot
pip3 install --user lark-parser
~~~

## Run the frontend

Run the following command in the root of the project:

~~~
$ python3 demo.py dataset/sources trident/rql.lark
~~~

Then you can access the demo page through [this url](https://localhost:5000/demo.html).

## Try Routing Query Language

Now click `Submit RA` button in the navigation bar, you will be prompted with a
dialogue box where you can type RQL scripts.

Start with the following script with two commands:

~~~
LOAD Colt AS topo

SHOW topo
~~~

You should see the topology plotted on the web page. Move the mouse over a link
and see what properties it has.

Now run the following script:

~~~
DEFINE COST hopcount, int, 1, add FOR EACH LINK IN topo

DEFINE PROPERTY capacity, int, 10000000 FOR EACH LINK IN topo

SHOW topo
~~~

Now move the mouse over a link. You should be able to see two more attributes:
`hopcount` and `capacity`, which is exactly the ones that you just defined with
the script.

Now run the following script:

~~~
OPT hopcount WHEN
SELECT src :-: dst
IN topology
WHERE (src::id = "n1" OR src::id = "n3") AND dst::id = "n2"
AS view

SHOW view
~~~

## RQL Commands

RQL supports the following commands:

1. LOAD command:

   `LOAD topology_name AS var`

   This command loads a topology (from the `dataset/sources/` directory) and
   saves the topology in a variable named `var`. For example, `LOAD Colt AS topo`
   will load the topology from `dataset/sources/Colt.grapml` and save it as a
   variable named `topo`.

2. SHOW command:

   `SHOW var`

   This command allows you to display the content of a variable. For example,
   `SHOW topo` will plot the topology named `topo`.

3. DEFINE command:

4. SET command:

5. SELECT command:

6. WATCH command:

7. DROP command:
