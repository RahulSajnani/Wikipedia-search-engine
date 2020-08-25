import nltk
import xml.etree.ElementTree as etree
import sys
import helper_functions
import re
import Stemmer


'''
Author: Rahul Sajnani
'''


class Indexer:
    '''
    Wikipedia dump indexer class

    Creates index for given XML file
    '''
    
    def __init__(self, xml_file_path, stop_words_file = "./stopwords.txt"):

        self.parser = etree.iterparse(xml_file_path, events = ("start", "end"))
        
        # Reading stop words list
        with open(stop_words_file, "r") as fp:
            self.stop_words = fp.readlines()
        
        self.stop_words = [word.strip("'") for word in self.stop_words]
        self.stemmer = Stemmer.Stemmer('english')
        self.postings_list = dict()

    def process_string(self, string):
        '''
        Removes stop words and tokenizes
        '''
        # Case folding
        string = string.lower()

        # Removing special symbols
        string = re.sub(r'[^A-Za-z0-9]+', r' ', string)
        
        string = string.split()
        
        tokens_dict = {}

        for word in string:
            if word not in self.stop_words:
                if len(word) > 1:
                    word = self.stemmer.stemWord(word)
                    if word in tokens_dict:
                        tokens_dict[word] += 1
                    else:
                        tokens_dict[word] = 1
                    
        return tokens_dict
        

    def extract_page_fields(self, page_body):
        '''
        Extracts infobox, category, links, and references
        '''
        # infobox and external links required
        page_references_list = re.findall("<ref>(.*?)</ref>", page_body)
        # if page_references_list != []:
        #     print("Reference list:", page_references_list)

        
        page_infobox_list = re.findall("\{\{Infobox (.*?)\}\}", page_body)
        # if page_infobox_list != []:
        #     print("Infobox list:", page_infobox_list)

        # Page categories
        page_category_list = re.findall("\[\[Category:(.*?)\]\]", page_body)
        # if page_category_list != []:
        #     print("Categories list:", page_category_list)
        
        body_list = self.process_string(page_body)
        # print(body_list)
        page_dict = {}

        

        pass



    def run(self):
        '''
        Run indexer
        '''

        # if page is detected
        page_detected = 0

        # if revision page
        is_revision = 0
        
        i = 0
        for event, element in self.parser:
            
            tag_name = element.tag.split("}")[-1]    
            
            if event == "start":

                if tag_name == "page":
                    # Start of page

                    is_revision = 0
                    page_detected = 1                  
                    page_title = ""
                    page_id = -1
                    page_infobox = ""
                    page_body = ""
                    page_category = ""


                elif tag_name == "revision":
                    # Revision page
                    is_revision = 1

                elif page_detected:
                    
                    if tag_name == "id" and not is_revision:
                        # update id if page is detected but is not revision page
                        page_id = element.text
                    
                    elif tag_name == "title":
                        page_title = element.text
                    
                    elif tag_name == "text":
                        page_body = element.text
                        
            elif event == "end":
                
                if tag_name == "page":    
                    
                    # print(page_id, " ", page_title)
                    if page_title is not None:
                        page_title = page_title.lower()

                    if page_body is not None:
                        self.extract_page_fields(page_body.lower())
                    page_detected = 0
                    is_revision = 0

            # Clearing element  
            element.clear()


if __name__ == "__main__":

    wikipedia_dump_path = sys.argv[1]
    index_path = sys.argv[2]

    indexer = Indexer(wikipedia_dump_path)
    indexer.run()
    # print(wikipedia_dump_path)