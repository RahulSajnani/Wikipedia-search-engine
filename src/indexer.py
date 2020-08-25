import nltk
import xml.etree.ElementTree as etree
import sys
import helper_functions

'''
Author: Rahul Sajnani
'''


class Indexer:
    '''
    Wikipedia dump indexer class

    Creates index for given XML file
    '''
    def __init__(self, xml_file_path):

        self.parser = etree.iterparse(xml_file_path, events = ("start", "end"))
    
    

    def extract_page_fields(self, page_id, page_title, page_body):
        '''
        Extracts infobox, category, links, and references
        '''




    def run(self):
        '''
        Run indexer
        '''

        # if page is detected
        page_detected = 0

        # if revision page
        is_revision = 0

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
                    
                    print(page_id, " ", page_title, " ", page_body)
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