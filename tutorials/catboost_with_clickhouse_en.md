## Starting the container

The tutorial uses a Docker container. Command to launch the container:
```bash
$ sudo docker run -it -p 8888:8888 yandex/tutorial-catboost-clickhouse
```
As a result, you can access Jupyter Notebook with tutorials for CatBoost and ClickHouse at `http://localhost:8888`:

* `kaggle_amazon_catboost.ipynb` - Demo of CatBoost features using [Amazon Employee Access Challenge](https://www.kaggle.com/c/amazon-employee-access-challenge) data.
* `catboost_with_clickhouse.ipynb` - Applying CatBoost models in ClickHouse (current document).

### VirtualBox image

A [VirtualBox image](https://yadi.sk/d/htNTv2VK3Q9RQ7) is available as an alternative to the Docker container. The same materials will be available at `http://localhost:8888` after launching it.

### Command prompt

You will need to use the command prompt in order to work with ClickHouse. You can use the command prompt from inside the Docker container or VirtualBox image. Another option is to use the `jupyter notebook` command prompt. Open the [Home](http://localhost:8888/tree) page and select `New->Terminal`. All further commands may be copied directly into the terminal window.

## Working with ClickHouse

ClickHouse supports a variety of different interfaces, including HTTP, JDBC, ODBC, and many third-party libraries for popular programming languages. However, this tutorial uses the native client over TCP.

### Command-line interface

The ClickHouse server is already running inside the Docker container. In order to connect to the server, type the command:

```bash
$ clickhouse client --host 127.0.0.1
```

As a result, ClickHouse shows an invitation for input:
```
:)
```

Try writing a "Hello, world!" query:
```SQL
:) SELECT 'Hello, world!'
```

If everything works, go to the next step.

### Using ClickHouse as a calculator

Run simple calculation queries: 

```SQL
:) SELECT 2 + 2 * 2
```

```SQL
:) SELECT cos(pi() / 3)
```

```SQL
:) SELECT pow(e(), pi())
```
The system.numbers table has a single column, called *number*. This column stores integer numbers starting from zero. Let's look at the first 10:

```SQL
:) SELECT number FROM system.numbers LIMIT 10
```
Now calculate the sum of squares for the first 100 integer numbers:
```SQL
:) SELECT sum(pow(number, 2))
FROM 
(
    SELECT *
    FROM system.numbers 
    LIMIT 101
) 
```
The last example was created using a **subquery** from the system.numbers table. First it selects the single *number* column with numbers from 0 to 100. Then it calculates the squares and totals them using the `sum` **aggregate function**.

## Create a table and insert data
Create a table for the train sample:
```SQL
:) CREATE TABLE amazon_train
(
    date Date MATERIALIZED today(), 
    ACTION UInt8, 
    RESOURCE UInt32, 
    MGR_ID UInt32, 
    ROLE_ROLLUP_1 UInt32, 
    ROLE_ROLLUP_2 UInt32, 
    ROLE_DEPTNAME UInt32, 
    ROLE_TITLE UInt32, 
    ROLE_FAMILY_DESC UInt32, 
    ROLE_FAMILY UInt32, 
    ROLE_CODE UInt32
)
ENGINE = MergeTree(date, date, 8192)
```
In order to insert data into ClickHouse, you will need to use the Linux command line. Use Crtl+C to exit ClickHouse (alternatively, type "quit", "logout", "exit;", "quit;", "q", or an equivalent). Then run the command:
```bash
$ clickhouse client --host 127.0.0.1 --query 'INSERT INTO amazon_train FORMAT CSVWithNames' < ~/amazon/train.csv
```
Check that data was inserted:
```bash
$ clickhouse client --host 0.0.0.0
```
```SQL
:) SELECT count() FROM amazon_train
```
Calculate the average for the ACTION column:
```SQL
:) SELECT avg(ACTION) FROM amazon_train
```

### Working with the trained model

Create a config file with the model configuration:
```XML
<models>
    <model>
        <!-- Model type. Now catboost only. -->
        <type>catboost</type>
        <!-- Model name. -->
        <name>amazon</name>
        <!-- Path to trained model. -->
        <path>/home/catboost/tutorial/catboost_model.bin</path>
        <!-- Update interval. -->
        <lifetime>0</lifetime>
    </model>
</models>
```
The ClickHouse configuration file should already have this setting:
```XML
<models_config>/home/catboost/models/*_model.xml</models_config>
```
To check it, run the command: `tail /etc/clickhouse-server/config.xml`

Let's make sure that the model is working. Calculate predictions for the first 10 rows from the table:
```SQL
:) SELECT 
    modelEvaluate('amazon', 
                  RESOURCE,
                  MGR_ID,
                  ROLE_ROLLUP_1,
                  ROLE_ROLLUP_2,
                  ROLE_DEPTNAME,
                  ROLE_TITLE,
                  ROLE_FAMILY_DESC,
                  ROLE_FAMILY,
                  ROLE_CODE) > 0 AS prediction, 
    ACTION AS target
FROM amazon_train
LIMIT 10
```
Now let's predict probability:
```SQL
:) SELECT 
    modelEvaluate('amazon', 
                  RESOURCE,
                  MGR_ID,
                  ROLE_ROLLUP_1,
                  ROLE_ROLLUP_2,
                  ROLE_DEPTNAME,
                  ROLE_TITLE,
                  ROLE_FAMILY_DESC,
                  ROLE_FAMILY,
                  ROLE_CODE) AS prediction,
    1. / (1 + exp(-prediction)) AS probability, 
    ACTION AS target
FROM amazon_train
LIMIT 10
```
Calculate LogLoss on the sample:
```SQL
:) SELECT -avg(tg * log(prob) + (1 - tg) * log(1 - prob)) AS logloss
FROM 
(
    SELECT 
        modelEvaluate('amazon', 
                      RESOURCE,
                      MGR_ID,
                      ROLE_ROLLUP_1,
                      ROLE_ROLLUP_2,
                      ROLE_DEPTNAME,
                      ROLE_TITLE,
                      ROLE_FAMILY_DESC,
                      ROLE_FAMILY,
                      ROLE_CODE) AS prediction,
        1. / (1. + exp(-prediction)) AS prob, 
        ACTION AS tg
    FROM amazon_train
)
```

## Integration with CatBoost

Instead of creating a table for the test sample, let's use the `catBoostPool` table function.
The column descriptions are in the file `/home/catboost/tutorial/amazon/test.cd`, which looks like this:
```
0	DocId	id
1	Categ	RESOURCE
2	Categ	MGR_ID
3	Categ	ROLE_ROLLUP_1
4	Categ	ROLE_ROLLUP_2
5	Categ	ROLE_DEPTNAME
6	Categ	ROLE_TITLE
7	Categ	ROLE_FAMILY_DESC
8	Categ	ROLE_FAMILY
9	Categ	ROLE_CODE
```

Take a look at the temporary table structure that is returned from `catBoostPool`:
```SQL
:) DESCRIBE TABLE catBoostPool('amazon/test.cd', 'amazon/test.tsv')

┌─name─────────────┬─type───┬─default_type─┬─default_expression─┐
│ Categ0           │ String │              │                    │
│ Categ1           │ String │              │                    │
│ Categ2           │ String │              │                    │
│ Categ3           │ String │              │                    │
│ Categ4           │ String │              │                    │
│ Categ5           │ String │              │                    │
│ Categ6           │ String │              │                    │
│ Categ7           │ String │              │                    │
│ Categ8           │ String │              │                    │
│ DocId            │ String │              │                    │
│ id               │ String │ ALIAS        │ DocId              │
│ RESOURCE         │ String │ ALIAS        │ Categ0             │
│ MGR_ID           │ String │ ALIAS        │ Categ1             │
│ ROLE_ROLLUP_1    │ String │ ALIAS        │ Categ2             │
│ ROLE_ROLLUP_2    │ String │ ALIAS        │ Categ3             │
│ ROLE_DEPTNAME    │ String │ ALIAS        │ Categ4             │
│ ROLE_TITLE       │ String │ ALIAS        │ Categ5             │
│ ROLE_FAMILY_DESC │ String │ ALIAS        │ Categ6             │
│ ROLE_FAMILY      │ String │ ALIAS        │ Categ7             │
│ ROLE_CODE        │ String │ ALIAS        │ Categ8             │
└──────────────────┴────────┴──────────────┴────────────────────┘
```
The table contains columns for each feature and aliases from the column description file. 
Calculate probability for the first 10 rows:
```SQL
:) SELECT 
    id,
    modelEvaluate('amazon', *) AS prediction,
    1. / (1. + exp(-prediction)) AS probability
FROM catBoostPool('amazon/test.cd', 'amazon/test.tsv')
LIMIT 10
```
You can use * in place of arguments for `modelEvaluate` when reading from `catBoostPool`.
Calculate the answer for the test sample and write the result to a file:
```SQL
SELECT 
    toUInt32(id) AS Id, 
    1. / (1 + exp(-modelEvaluate('amazon', *))) AS Action
FROM catBoostPool('amazon/test.cd', 'amazon/test.tsv') 
INTO OUTFILE 'submission.tsv'
FORMAT CSVWithNames
```
Submit the result on [Kaggle](https://www.kaggle.com/c/amazon-employee-access-challenge/leaderboard) (you can download `submission.tsv` from the Docker container using the `jupyter notebook` interface). Where do you rank on the leaderboard?
