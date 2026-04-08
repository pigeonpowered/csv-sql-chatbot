import duckdb
import pandas as pd
import openai
from openai import OpenAI
import marko

class SqlPrompt:
    
    """
    Class to handle the prompt generation
    """

    def __init__(self, table):
        self.table = table
        self.question = None
        self.message = None
        self.client = OpenAI()
        self.schema = None
        self.definitions = None
        self.openai_response = None
        self.query = None
    
    def get_table_schema(self):
        data = pd.read_csv('./data/PS_ACORD_HEADER.csv')

        tbl_describe = duckdb.sql("DESCRIBE SELECT * FROM data;")
        col_attr = tbl_describe.df()[["column_name", "column_type"]]
        col_attr["column_joint"] = col_attr["column_name"] + " " +  col_attr["column_type"]
        self.schema = str(list(col_attr["column_joint"].values)).replace('[', '').replace(']', '').replace('\'', '')

    def get_table_definitions(self):
        definitions_data = pd.read_csv('./data/PS_ACORD_HEADER_aliases.csv')

        tbl_describe = duckdb.sql("SELECT * FROM definitions_data;").show(max_width=10000)
        self.definitions = str(tbl_describe)

    def set_prompt(self, question):
        self.get_table_schema()
        self.get_table_definitions()

        system_template = """
            Given the following SQL table, your job is to write queries given a user’s request. \n

            CREATE TABLE {} ({}) \n
                        
            Use the following table to describe each column in the SQL table. Use the following table to learn what each column contains, and use that knowledge to understand what data the user is asking for.

            {}

            Example prompt from user: Write a SQL query that returns - Give me an active policy from ALIP in California that has a policy value of over 100000.
            Sample query returned from prompt: Sure! Here is the query: \n ``` \n SELECT * FROM {}
            WHERE CarrierAdminSystem LIKE '%ALIP%'
            AND Jurisdiction LIKE '%CA%'
            AND SrcPolicyStatus LIKE '%Active%' AND PolicyValue > 100000
            AND PolNumber NOT LIKE '%-sdel%' \n```\n

            Example prompt from user: Write a SQL query that returns - Give me active policy from ALIP that has a policy value over 100000.
            Sample query returned from prompt: Sure! Here is the query: \n``` \n SELECT * FROM {} \n 
            WHERE CarrierAdminSystem LIKE '%ALIP%'
            AND SrcPolicyStatus LIKE '%Active%' AND PolicyValue > 100000
            AND PolNumber NOT LIKE '%-sdel%' \n```\n

            Example prompt from user: Write a SQL query that returns - Give me an indexed annuity from ID3 that is surrendered.
            Sample query returned from prompt: Sure! Here is the query: \n SELECT * FROM {} \n 
            WHERE CarrierAdminSystem LIKE '%ID3%'
            AND ProductType LIKE '%Indexed Annuity%'
            AND PolicyStatus LIKE '%Surrendered%'
            AND PolNumber NOT LIKE '%-sdel%' \n ``` \n

            Always return a query for a single row unless the user specifically asks for multiple policies or a list of policies.

            For policy status, search both the columns "SrcPolicyStatus" and "PolicyStatus".

            Always abbreviate state names to their two letter abbreviation instead of the full name. 
            
            Jurisdictions can always only be US state abbreviations. If the user asks for jurisdiction outside of a US state, re-prompt the user.

            Always use "LIKE" instead of equals for SQL queries.

            Always include "AND PolNumber NOT LIKE '%-sdel%'".

            Insert line breaks before 'AND' and 'WHERE'.

            If the user says a proper noun before the word "policy", that is the product name of the policy.

            Only use columns defined within the SQL table. If the user asks for a column that does not exist, ask for more clarification.

                        """
        user_template = "Write a SQL query that returns - {}"

        system_prompt = system_template.format(self.table, self.schema, self.definitions, self.table, self.table, self.table)
        user_prompt = user_template.format(question)
        self.message =  [
                        {
                          "role": "system",
                          "content": system_prompt
                        },
                        {
                          "role": "user",
                          "content": user_prompt
                        }
                        ]
        
    def openai_request(self, 
                       openai_api_key,
                       model = "gpt-4o-mini", 
                       temperature = 0, 
                       max_tokens = 256, 
                       frequency_penalty = 0,
                       presence_penalty= 0):
        openai.api_key = openai_api_key
        self.openai_response = self.client.chat.completions.create(
            model = model,
            messages = self.message,
            temperature = temperature,
            max_tokens = max_tokens,
            frequency_penalty = frequency_penalty,
            presence_penalty = presence_penalty)
        
        self.query = marko.convert(self.openai_response.choices[0].message.content.strip());
    
    def ask_question(self, question, openai_api_key):
        self.set_prompt(question)
        self.openai_request(openai_api_key = openai_api_key,
                            model = "gpt-4o-mini", 
                            temperature = 0, 
                            max_tokens = 256, 
                            frequency_penalty = 0,
                            presence_penalty= 0)