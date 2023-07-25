# Overview:
The SQS Messages are read, transformed- encrypting PII data using MD5 Hashing algorithm and further
written into Postgres database.

## Folder Structure:
    root
    |_src: logger.py for logging
    |_main.py:logic implementation
        |_Class SqsMessages: Methods to read and transform data into desired format
        |_Class Database: To handle Postgres database operation
    |_requirements.txt: modules to be installed in the Docker image
    |_DockerFile and docker-compose.yml: Docker image with python 3.9 and container configuration
    |_Docs: contains images for Readme.md

### How to run?
Fork the repo and run the below command to execute
```commandline
   docker-compose up --build
   python .src/main.py
```
##### Execution flow:
1) LocalStack docker image is created
2) PostgresSQL docker image in created
3) post query_url display -> run main.py
4) The respective data is inserted into the table user_logins and displayed as shown below

Sample:
![postgres_insert_records](Docs/postgres_insert_records.PNG)


Note: For further enhancements, the Docker file can be optimized to automate the execution
by writing a bash script to handle execution. 

### Questions
1) How would you deploy this application in production?

We can containerize this as an application and deploy it in production.
Note:A docker file is written to which this can be deployed in production. This is not the end product, will need
further enhancement to automate execution
AWS Lambda function can be used as a trigger to process each new batch of
SQS messages.
After the code is reviewed, tested and deployed in beta environments, a new release needs to be
tagged and deployed in production(master_branch).

2) What other components would you want to add to make this production ready?

Need to add AWS Lambda to trigger the transformation step when new set of messages are encountered.
Add CloudWatch to monitor and notify for scaling the instance. Would be best to store the 
corresponding secret_key in a secured fashion for future decryption of the PII data.


3) How can this application scale with a growing dataset.

With growing SQS messages,  a load balancer can be used to optimally transform the data.
For example if the SQS Queue threshold reaches its maximum capacity, CloudWatch can be used which
will notify auto-scaling-group to create new EC2 instances to handle the high influx of messages

On the database side, AWS RDS or Redshift can be used to store large and increasing data without
having to worry about its scaling, security, data access, availability and more.

4) How can PII be recovered later on?

The PII columns are masked using MD5 Hashing algorithm using a secret_key(extracted from raw data-(MD5OfBody))
Note: User_id could also be used as a secret_key(However, as in the given table schema it is not shown that user_id is unique i decided to use MD5OfBody value as secret_key)
Recovering PII: The secret_key needs to be stored for the respective user and later can be used to decrypt to its original form


5) What are the assumptions you made?
* The Postgres docker image is working as expected after testing locally. However, reading the
query url 
`awslocal sqs receive-message --queue-url http://localhost:4566/000000000000/login-queue`
was throwing `UnkownOperationException`
Upon debugging I found out that AWS region and credentials were invalid. Reached out to the recruiter
for assistance. However, was asked to use my best judgement.
Therefore, upon further debugging, found out from LocalStack SQS docs that `?Action=GetQueueUrl&QueueName=<QueueName>` needed
to be added at the end of the query-url for it to work.

- LocalStack Doc fix - [link](https://docs.localstack.cloud/user-guide/aws/sqs/)

With this was able to get the data in the form of XML data.
Note: I was unable to use Boto3 to automate reading all of the SQS messages in the queue due to the above issue.
Hence, read the data as an url and converted the same using xmltodict and further processed it using
Regex.

* app_version: is not in the required schema format to insert into the PostgresSQL table.
For Example: `app_version=2.3.0`  was converted to `230`to be inserted as an integer
into the table.
* Without Boto3 to read all the SQS messages at once, I assumed that for each run only a single record is available and hence is processed and inserted into the table.
  (1:1 mapping)
