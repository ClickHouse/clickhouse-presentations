## Запуск контейнера

Для работы с туториалом будем использовать Docker - контейнер. Запускаем контейнер командой

```bash
$ sudo docker run -it -p 8888:8888 yandex/tutorial-catboost-clickhouse

```

После запуска контейнера по адресу `http://localhost:8888` должен быть доступен `jupyter notebook` с материалами туториалов CatBoost и ClickHouse:

* `kaggle_amazon_catboost_ru.ipynb` - Демонстрация возможностей CatBoost на примере данных [Amazon Employee Access Challenge](https://www.kaggle.com/c/amazon-employee-access-challenge)
* `catboost_with_clickhouse.ipynb` - Применение моделей CatBoost в ClickHouse (содержание данного документа)

Для туториала "применение моделей CatBoost в ClickHouse" можно обучить модель, пройдя туториал по работе с CatBoost, или использовать обученную из контейнера.

### Образ VirtualBox

В качестве альтернативы использования Docker - контейнера есть возможность использовать [образ виртуальной машины VirtualBox](https://yadi.sk/d/htNTv2VK3Q9RQ7). Аналогично, после запуска контейнера по адресу `http://localhost:8888` должен быть доступен `jupyter notebook` с материалами туториалов CatBoost и ClickHouse.

### Работа с командной строкой

Для работы с ClickHouse потребуется доступ к командной строке контейнера или образа VirtualBox. В качестве одного из возможных вариантов удобно использовать возможности `jupyter notebook`. Для этого на странице [Home](http://localhost:8888/tree) выбираем `New->Terminal`. Все последующие команды достаточно копировать в окно терминала.

## Работа с ClickHouse

ClickHouse поддерживает работу различными интерфейсами, включая HTTP, JDBC, ODBC, а также множество сторонних библиотек для популярных языков программирования. Но в данном туториале мы будем использовать нативный клиент, работающий через TCP. Так будет гораздо нагляднее.

### Интерфейс командной строки

ClickHouse server уже запущен внутри Docker контейнера. Для подключения достаточно ввести консольную команду

```bash
$ clickhouse client --host 127.0.0.1
```

В результате ClickHouse покажет приглашение для ввода команд
```
:)
```

Напишем запрос "Hello, world!"
```SQL
:) SELECT 'Hello, world!'
```

Если все работает, переходим к следующему шагу.

### ClickHouse как калькулятор

Выполним простейшие вычисления. 

```SQL
:) SELECT 2 + 2 * 2
```

```SQL
:) SELECT cos(pi() / 3)
```

```SQL
:) SELECT pow(e(), pi())
```
Таблица system.numbers содержит единственный столбец number. В этом столбце записана бесконечная последовательность целых положительных чисел. Посмотрим на первые 10

```SQL
:) SELECT number FROM system.numbers LIMIT 10
```
Теперь посчитаем сумму квадратов первых 100 натуральных чисел
```SQL
:) SELECT sum(pow(number, 2))
FROM 
(
    SELECT *
    FROM system.numbers 
    LIMIT 101
) 
```
Последний пример был написан при помощи **подзапроса** из таблицы system.numbers. Сначала выбираем единственный столбец number с числами от 0 до 100, затем возводим в квадрат и суммируем с использованием **агрегатной функции** sum.

## Создание таблицы и загрузка данных
Создадим таблицу для обучающей выборки и загрузим туда данные.
Таблица для обучающей выборки:
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
Вставлять данные будем в потоковом режиме с использованием командной строки Linux. Выходим из ClickHouse при помощи Crtl+C или написав команду "exit" (также работают команды "quit", "logout", "учше", "йгше", "дщпщге", "exit;", "quit;", "logout;", "учшеж", "йгшеж", "дщпщгеж", "q", "й", "q", "Q", ":q", "й", "Й", "Жй"). Теперь набираем в консоли:
```bash
$ clickhouse client --host 127.0.0.1 --query 'INSERT INTO amazon_train FORMAT CSVWithNames' < ~/amazon/train.csv
```
Проверим, что данные загрузились

```bash
$ clickhouse client --host 127.0.0.1
```
```SQL
:) SELECT count() FROM amazon_train
```
Посчитаем среднее значение по столбцу ACTION
```SQL
:) SELECT avg(ACTION) FROM amazon_train
```

### Работа с обученной моделью

Создаем файл с конфигурацией модели
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
В конфигурации ClickHouse уже прописан параметр
```XML
<models_config>/home/catboost/models/*_model.xml</models_config>
```
В этом можно убедиться, выполнив команду `tail /etc/clickhouse-server/config.xml`

Проверим, что модель работает. Посмотрим на предсказания для первых 10 строк таблицы.
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
Теперь посмотрим на предсказанную вероятность
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
Посчитаем LogLoss на всей выборке
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

## Использование пула CatBoost

Для тестовой выборки не будем создавать таблицу, а вместо этого воспользуемся табличной функцией `catBoostPool`.
Описание формата столбцов пула находится в файле `/home/catboost/tutorial/amazon/test.cd` и выглядит так:

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

Посмотрим на структуру временной таблицы, которую создает catBoostPool
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
Таблица содержит столбцы со значениями признаков и алиасы с именами из файла описания столбцов.
Посчитаем вероятность для первых 10 строк
```SQL
:) SELECT 
    id,
    modelEvaluate('amazon', *) AS prediction,
    1. / (1. + exp(-prediction)) AS probability
FROM catBoostPool('amazon/test.cd', 'amazon/test.tsv')
LIMIT 10
```
При чтении из catBoostPool достаточно указать __*__ в качестве аргументов функции `catBoostPool`
Посчитаем ответ для всей выборки и запишем результат в файл.
```SQL
SELECT 
    toUInt32(id) AS Id, 
    1. / (1 + exp(-modelEvaluate('amazon', *))) AS Action
FROM catBoostPool('amazon/test.cd', 'amazon/test.tsv') 
INTO OUTFILE 'submission.tsv'
FORMAT CSVWithNames
```
Сделаем посылку на [Kaggle](https://www.kaggle.com/c/amazon-employee-access-challenge/leaderboard) (файл submission.tsv можно скачать из Docker контейнера при помощи интерфейса jupyter). Какое место получилось занять у вас?
