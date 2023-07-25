import boto3
import requests
import xmltodict
import regex as re
import psycopg2
import datetime
import hashlib
from logger import get_logger


class SqsMessages:
    """
    This class Extracts SQS Messages, masks required data types, formats the data according to PostgresSQL table schema
    """
    def __init__(self, query_url):
        self.__query_url = query_url

    def mask_dataTypes(self, data_dict:dict, column_names:list):
        """
        This methods masks the required column names using MD5 hashing algorithm with a secret_hash_key which can be
        later used to retrieve the data in the decrypted format.
        Assumption: The secret key from xml data(MD5OfBody) is used. Note: user_id could have also been used to mask the data
        :param data_dict: Dictionary data type consisiting of column names and value as key value pairs
        :param column_names: List of columns to be hashed
        :return: Dictionary with hashed values
        """
        try:
            for col in column_names:
                data_dict[col] = hashlib.md5(data_dict[col].encode('utf-8') + data_dict['secret_key'].encode('utf-8')).hexdigest()
        except Exception as e:
            logger.error(f"Failed to Mask the column due to: {e}")

        return data_dict

    def format_dataTypes(self, data_dict):
        """
        :param data_dict: Data Dictionary consisting of data and values as Key value pairs
        :return: Correctly formatted data that matches the PostgresSQL data schema
        """
        try:
            data_dict['create_date'] = str(data_dict['create_date'])
            data_dict['user_id'] = str(data_dict['user_id'])
            data_dict['app_version'] = int(data_dict['app_version'].replace('.', ""))
            data_dict['device_type'] = str(data_dict['device_type'])
            data_dict['ip'] = str(data_dict['ip'])
            data_dict['device_id'] = str(data_dict['device_id'])
            data_dict['locale'] = str(data_dict['locale'])
            logger.info("Completed data formatting")

        except Exception as e:
            logger.error(f'Failed to format the dataTypes due to: {e}')
        return data_dict

    def extract_message_values(self):
        """
        Extracts data from SQS query url, converts raw data into key value pairs using xmltodict python library.
        Regular expressions are used to extract column names and values and are further stored in dictionary: this
        dictionary is passed around the methods for further processing until inserting into the database.
        :return: Dictionary(Dict) with column value and name as key-value pairs
        """
        try:
            response = requests.get(self.__query_url)
            data = xmltodict.parse(response.content)
            Dict = dict()
            Dict['secret_key'] = re.findall(r"(?<='MD5OfBody', ').*(?='\), \('Body')", str(data.values()))[0]
            Dict['create_date'] = re.findall(r'(?<=doc\/)([0-9]+-[0-9]+-[0-9]+)', str(data.values()))[0]
            columns = re.findall(r"(?<='Body', '{).*(?=})", str(data.values()))

            if not columns[0] or Dict['create_date'] is None or Dict['secret_key'] is None:
                raise Exception('All the values were not present in the SQS Message!!!')

            split_data = columns[0].split(",")

            for val in split_data:
                Dict[val.split(':')[0].replace('"', '').strip(" ")] = val.split(':')[1].replace('"', '').strip(" ")

            Dict = self.mask_dataTypes(Dict, ['ip', 'device_id'])
            Dict = self.format_dataTypes(Dict)

        except Exception as e:
            logger.error(f"Failed to extract_message_values due to :{e}")
        return Dict

class Database():
    """
    This Class receives a database connection to PostgresSQL, and has methods to support viewing tables, inserting
    records and closing connections.
    """
    def __init__(self, connection):
        self.__connection = connection

    def get_connection(self):
        return self.__connection

    def close_connection(self):
        self.__connection.close()

    def show_db(self, table_name:str):
        # cursor = self.__connection.cursor()
        self.__connection.execute(f"SELECT * from {table_name};")
        result = self.__connection.fetchall()
        print(result)

    def insert_into_table(self, dict_data):
        self.__connection.execute("""
            insert into user_logins(user_id, device_type, masked_ip, masked_device_id, locale, app_version, create_date) values(%(user_id)s,%(device_type)s,%(ip)s,%(device_id)s,%(locale)s,%(app_version)s,%(create_date)s)
            """, dict_data)



def main():
    query_url = 'http://localhost:4566/000000000000/login-queue?Action=ReceiveMessage'
    sqs = SqsMessages(query_url)
    ###### Extract SQS Message from queue #############
    data_dict = sqs.extract_message_values()

    try:
        con = psycopg2.connect(
            database="postgres",
            user="postgres",
            password="postgres",
            port='5432',
            host='localhost'
        )
        cursor_obj = con.cursor()
        database = Database(cursor_obj)

        ###### Viewing table user_logins #######
        logger.info("Viewing user_logins table before inserting new record")
        print('Table before inserting new record')
        database.show_db('user_logins')
        logger.info("Inserting record into PostgresSQL")

        ######## Inserting new extracted record into user_logins table #########
        database.insert_into_table(data_dict)
        logger.info("Successfully inserted record into PostgresSQL")
        logger.info("Viewing user_logins table after insertion of new record")
        print('Table after inserting new record')
        database.show_db('user_logins')

    except Exception as e:
        logger.error(f"Failed to process! due to {e}")
        raise
    finally:
        logger.info("Closing Connection")
        if database.get_connection():
            database.close_connection()


if __name__ == '__main__':
    logger = get_logger()
    main()
