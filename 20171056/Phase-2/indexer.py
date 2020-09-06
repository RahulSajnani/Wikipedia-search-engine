try:
    import xml.etree.cElementTree as etree
except ImportError:
    import xml.etree.ElementTree as etree

import sys
import config
import re
import Stemmer
import os
import glob
import gc
import heapq, math
import linecache

'''
Author: Rahul Sajnani
'''

class MergeIndex:
    '''
    K way index merge class
    '''
    def __init__(self, page_count, index_path, index_count):
        
        super().__init__()

        self.page_count = page_count
        self.index_directory = index_path
        self.index_count = index_count
        self.categories = sorted(["references", "body", "infobox", "title", "category", "links"])
        self.files_dictionary = self.get_index_file_dict()
        self.file_mapping = config.alphabet_file_mapping
        # print(self.files_dictionary)
    
    def get_index_file_dict(self):
        '''
        Get index file names
        '''
        files_dictionary = {}
        for field in self.categories:
            files_dictionary[field] = []
            for i in range(self.index_count):
                file_name = "index_%s_%d.txt" % (str(field), i)
                files_dictionary[field].append(os.path.join( self.index_directory,file_name))
        
        files_dictionary["tokens"] = []
        for i in range(self.index_count):
                file_name = "tokens_%d.txt" % (i)
                files_dictionary["tokens"].append(os.path.join( self.index_directory,file_name))

        return files_dictionary

    def read_token_line(self, line):
        '''
        Extract tokens and line numbers given the line
        '''

        words = line.split()
        if len(words) == 0:
            return None
        token_pair = (words[0], [])
        for i in range(1, len(words)):
            token_pair[1].append(int(words[i]))
        return token_pair


    def merge_postings_list(self, postings_dict, repeated_dict_list):
        '''
        K way merge posting's list for words that repeat across multiple blocks
        '''

        combined_postings_list = {}

        for field in self.categories:
            doc_id_list = []
            combined_postings_list[field] = {}
            current_posting_list = [postings_dict[field]["postings_list"]]    
            for tokens_dict in repeated_dict_list:
                if len(tokens_dict[field]["postings_list"]) > 0:
                    current_posting_list.append(tokens_dict[field]["postings_list"])

            merged_list = heapq.merge(*current_posting_list)
            
            for idx, doc_pair in enumerate(merged_list):
                doc_id_list.append(doc_pair)
            
            
            if len(doc_id_list):
                combined_postings_list[field]["postings_list"] = doc_id_list
            else:
                combined_postings_list[field]["postings_list"] = []

            
        return combined_postings_list

    def pop_token(self, heap, file_pointers):
        '''
        Pops token and reads the next line from file
        '''
        token_pair = heapq.heappop(heap)
        fp = file_pointers[token_pair[1][-1]]
        read_token = self.read_token_line(fp.readline())
        
        if read_token is not None:
            # If file is not empty
            read_token[1].append(token_pair[1][-1])
            heapq.heappush(heap, read_token)
        else:
            # Once index is complete for file delete older indexes
            for field in self.categories:
                path = self.files_dictionary[field][token_pair[1][-1]]
                os.remove(path)
                print("Deleting index file ", path)
            
            fp.close()
            os.remove(self.files_dictionary["tokens"][token_pair[1][-1]])
            print("Deleting index file ", self.files_dictionary["tokens"][token_pair[1][-1]])
            
        return token_pair

    def decode_line(self, line):
        '''
        Decode line from the file containing posting's list
        '''
        
        line_dict = {}
        line = line.split()
        
        # line_dict["size"] = int(line[0])
        line_dict["postings_list"] = []
        
        for i in range(0, len(line), 2):
            line_dict["postings_list"].append((int(line[i]), int(line[i + 1])))

        return line_dict

    def get_all_postings_list(self, token_pair, files_dictionary):
        '''
        Get postings list for all categories for a given token
        Token_pair order: ("token", [body_line, category_line, external_links_line, infobox_line,  reference_line, title_line, file_pointer_index])
        '''
        
        token_dictionary = {}
        for field in self.categories:
            if files_dictionary.get(field) is not None:
                if token_pair[1][self.categories.index(field)] != 0:
                    file_name = files_dictionary[field][token_pair[1][-1]]
                    line = linecache.getline(file_name, int(token_pair[1][self.categories.index(field)]))
                    token_dictionary[field] = self.decode_line(line)
                else:
                    token_dictionary[field] = {"postings_list": []}

            else:
                token_dictionary[field] = {"postings_list": []}

        return token_dictionary

    def write_posting_dict(self, token, posting_dict, file_output_pointers):
        '''
        Write postings list to file
        '''
        token_write_string = str(token)
        block = config.alphabet_file_mapping[token[0]]
        # print(posting_dict)
        for field in self.categories:
            
            df = len(posting_dict[field]["postings_list"])
            if df:
                write_string = ""
                for tuple_iter in posting_dict[field]["postings_list"]:
                    write_string += "%d %.2f " % (tuple_iter[0], (math.log((1 + tuple_iter[1]), 10) * math.log(self.page_count / df, 10)))
                
                write_string += "\n"
                line = file_output_pointers[field][block][1]
                file_output_pointers[field][block][0].write(write_string)
                file_output_pointers[field][block][1] = line + 1
                token_write_string += " %d" % line
            else:
                token_write_string += " 0"
        token_write_string += "\n"
        # print(token_write_string)
        file_output_pointers["tokens"][0].write(token_write_string)
        file_output_pointers["tokens"][1] += 1

    def merge_files(self):
        '''
        Merge files given 
        '''
        files_dictionary = self.files_dictionary
        output_directory = self.index_directory
        
        token_files = files_dictionary["tokens"]
        file_pointers = []
        tokens_heap = []
        file_output_pointers = {}
        
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)

        # Output of merged index
        for field in self.categories:
            file_output_pointers[field] = []
            for i in range(config.max_division):
                 file_output_pointers[field].append([open(os.path.join(output_directory, ("index_block_%d_%s.txt" % (i, str(field)))), "w"), 1])
                 
        file_output_pointers["tokens"] = [open(os.path.join(output_directory, "tokens.txt"), "w"), 1]
        # print(file_output_pointers)
        # del(files_dictionary["tokens"])
        
        for token_file_name in token_files:
            fp = open(token_file_name, "r")
            token_pair = self.read_token_line(fp.readline())
            file_pointers.append(fp)
            if token_pair:
                token_pair[1].append(len(file_pointers) - 1)
            heapq.heappush(tokens_heap, token_pair)
            
        while len(tokens_heap) > 0:
            
            token_pair = self.pop_token(tokens_heap, file_pointers)
            posting_dict = self.get_all_postings_list(token_pair, files_dictionary)
            repeated_token_list = []

            if len(tokens_heap):
                while token_pair[0] == tokens_heap[0][0]:
                    token_pair_2 = self.pop_token(tokens_heap, file_pointers)
                    posting_dict_2 = self.get_all_postings_list(token_pair_2, files_dictionary)
                    repeated_token_list.append(posting_dict_2)
                    # posting_dict = merge_postings_list(posting_dict, posting_dict_2)
                if len(repeated_token_list):
                    merged_dict = self.merge_postings_list(posting_dict, repeated_token_list)
                    posting_dict = merged_dict
            
            self.write_posting_dict(token_pair[0], posting_dict, file_output_pointers)
            repeated_token_list.clear()

class Indexer:
    '''
    Wikipedia dump indexer class

    Creates index for given XML file
    '''
    
    def __init__(self, xml_directory_path, index_directory, stop_words_file):

        self.xml_files = sorted(glob.glob(os.path.join(xml_directory_path, "enwiki-*")))
        self.index_count = 0
        self.titles = ""
        self.stem_dictionary = {}
        
        
        self.save_page_freq = 20000
        # Reading stop words list
        with open(stop_words_file, "r") as fp:
            self.stop_words = fp.readlines()
        self.stop_words_dict = {}
        # self.stop_words = [word.strip("'") for word in self.stop_words]
        for word in self.stop_words:
            self.stop_words_dict[word.split("\n")[0]] = 1

        self.stemmer = Stemmer.Stemmer('english')
        self.postings_dictionary = dict()
        self.index_directory = index_directory
        self.page_counter = 0
        if not os.path.exists(self.index_directory):
            os.makedirs(self.index_directory)
        self.titles_file_pointer = open(os.path.join(index_directory, "titles.txt"), "w")
        # print(self.stop_words)

    def process_page(self, page_dict):
        '''
        Removes stop words and tokenizes
        '''
        
        tokens_dict = {}
        total_words = 0
        for key in page_dict:    
            if key != "id":
                string = page_dict[key]
                tokens_dict[key] = dict()
                # Case folding
                string = string.lower()
                # Removing special symbols
                string = re.sub(r'[^A-Za-z0-9]+', r' ', string)
                string = string.split()
                
                for word in string:
                    total_words += 1
                    # if word not in self.stop_words:
                    if key != "title":
                        if self.stop_words_dict.get(word) is None:    
                            if self.stem_dictionary.get(word) is None:
                                self.stem_dictionary[word] = self.stemmer.stemWord(word)
                            word = self.stem_dictionary[word]
                            if tokens_dict[key].get(word) is not None:
                                tokens_dict[key][word] += 1
                            else:
                                tokens_dict[key][word] = 1
                    else:
                        if tokens_dict[key].get(word) is not None:
                            tokens_dict[key][word] += 1
                        else:
                            tokens_dict[key][word] = 1


        return tokens_dict, total_words        

    def process_tokens_dict(self, id, tokens_dict):
        '''
        Create posting list from tokens dictionary 
        '''
        # postings_dict = {}

        for key in tokens_dict:
            if self.postings_dictionary.get(key) is None:
                self.postings_dictionary[key] = {}
            
            for token in tokens_dict[key]:
                
                if self.postings_dictionary[key].get(token) is None:
                    self.postings_dictionary[key][token] = []
                
                self.postings_dictionary[key][token].append((id, tokens_dict[key][token]))
                

    def get_external_links(self, body):
        '''
        Get external links
        '''

        external_links = []
        lines = body.split("==")[-1]
        lines = lines.split("\n")

        for line in lines:
            if re.match(r"\*(.*)", line):
                external_links.append(line)

        return " ".join(external_links)
        
    #     pass
    def create_postings_list(self, page_dictionary):
        '''
        Extracts infobox, category, links, and references
        '''

        page_body = page_dictionary["body"]
        if page_body is not None:

            # removing http[s]? links
            page_body = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',' ',page_body,flags = re.DOTALL)
            # removing comments
            page_body = re.sub('<!--.*?-->',' ',page_body,flags = re.DOTALL)
            # removing math equations
            page_body = re.sub('<math([> ].*?)(</math>|/>)',' ',page_body,flags = re.DOTALL)
            # removing files
            page_body = re.sub(r'\[\[([fF]ile:|[iI]mage)[^]]*(\]\])',' ',page_body,flags = re.DOTALL)
            # removing cite tags
            page_body = re.sub(r'{{v?cite(.*?)}}', " ", page_body, re.DOTALL | re.I)
            
            page_body = re.sub(r'{\|(.*?)\|}', " ", page_body,re.DOTALL)
            # obtaining references
            page_references = " ".join(re.findall("<ref>(.*?)</ref>", page_body))
            # obtaining infobox
            page_infobox = " ".join(re.findall(r"\{\{Infobox(.*?)\}\}", page_body, flags = re.DOTALL))
            # obtaining categories
            page_category = " ".join(re.findall(r"\[\[Category:(.*?)\]\]", page_body))
            # obtaining page external links
            page_links = self.get_external_links(page_body)
            
            # Cleaning body
            page_body = re.sub('<.*?>',' ',page_body,flags = re.DOTALL)
            page_body = re.sub('{{([^}{]*)}}',' ',page_body,flags = re.DOTALL)
            page_body = re.sub('{{([^}]*)}}',' ',page_body,flags = re.DOTALL)
            
            page_dictionary["category"] = page_category
            page_dictionary["infobox"] = page_infobox
            page_dictionary["references"] = page_references
            page_dictionary["links"] = page_links
            page_dictionary["body"] = page_body
            # page_body = re.sub(r"(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)", r" ", page_body)
        else:
            page_dictionary["category"] = ""
            page_dictionary["infobox"] = ""
            page_dictionary["references"] = ""
            page_dictionary["links"] = ""
            page_dictionary["body"] = ""
            

        tokens_dict, total_words = self.process_page(page_dictionary)
        self.process_tokens_dict(page_dictionary["id"], tokens_dict)

        return total_words

    def write_index(self):
        '''
        Writing index to respective files
        '''
        dict_lines = {}
        
        for key in (self.postings_dictionary):
            # dict_lines[key] = {}
            filename = "index_%s_%d.txt" % (str(key), self.index_count)
            fp = open(os.path.join(self.index_directory, filename), "w")
            line = 1
            write_string = ""
            for token in sorted(self.postings_dictionary[key]):
                if dict_lines.get(token) is None:
                    dict_lines[token] = {}
                write_string += ""#str(length_list)
                for tuple_iter in sorted(self.postings_dictionary[key][token]):
                    # Writing doc id and frequency
                    write_string += " %s %s" % (str(tuple_iter[0]), str(tuple_iter[1]))
                dict_lines[token][key] = line
                line += 1
                write_string += "\n"

                # Write to file if the lines are more than 5000 and clear
                if line % 5000 == 0:
                    fp.write(write_string)
                    write_string = ""

            if write_string != "":
                fp.write(write_string)
            
            fp.close()

        write_string = ""
        categories = [key for key in sorted(self.postings_dictionary.keys())]
        for token in sorted(dict_lines):
            filename = "tokens_%d.txt" % self.index_count
            fp = open(os.path.join(self.index_directory, filename), "w")
            line = 1
            write_string += str(token)
            for key in categories:
                # get length of posting list
                if dict_lines[token].get(key) is None:
                    write_string += " 0"
                else:
                    write_string += " %s" % (str(dict_lines[token][key]))
            
            write_string += "\n"
            line += 1

            # Write to file if the lines are more than 5000 and clear
            if line % 10000 == 0:
                fp.write(write_string)
                write_string = ""
        
        if write_string != "":
            fp.write(write_string)
        
        self.titles_file_pointer.write(self.titles)
        self.titles = ""
        fp.close()

        self.index_count += 1
        self.postings_dictionary.clear()
        self.stem_dictionary.clear()
        dict_lines.clear()
        gc.collect()

    def merge_indexes(self):
        '''
        Performs k way merge of index files
        '''

        print("Merging files")
        merger = MergeIndex(page_count = self.page_counter, index_path = self.index_directory, index_count = self.index_count)
        merger.merge_files()

    def run(self):
        '''
        Run indexer
        '''

        for xml_file in self.xml_files:
            print("Reading file %s" % xml_file)
            tags_list = []
            first = True
            root = 0
            total_words = 0

            parser = etree.iterparse(xml_file,  events = ("start", "end"))
            for event, element in parser:
                
                tag_name = element.tag.split("}")[-1]    
                if event == "start":
                    
                    tags_list.append(tag_name)
                    
                    # Saving root element to clear in element tree
                    if first:
                        first = False
                        root = element
                        
                    if tag_name == "page":
                
                        page_dict = {}
                        page_title = ""
                        page_id = -1
                        page_body = ""                    
                            
                elif event == "end":
                    
                    tags_list.pop()

                    if tag_name == "id" and tags_list[-1] == "page":
                            # update id if page is detected but is not revision page       
                            page_id = int(element.text)
                        
                    elif tag_name == "title":
                            page_title = element.text
                        
                    elif tag_name == "text":
                            page_body = element.text
                        
                    elif tag_name == "page":

                        self.page_counter += 1
                        # print(page_id, " ", page_title)
                        page_dict = {"id": self.page_counter, "title": page_title, "body": page_body}
                        self.titles += page_title + "\n"
                        total_words += self.create_postings_list(page_dict)
                        root.clear()
                    
                        if self.page_counter % self.save_page_freq == 0:
                            # print(self.page_counter, self.save_page_freq)
                            self.write_index()
                    # Clearing element  
                    element.clear()

                last_tag = tag_name

        if self.postings_dictionary:
            self.write_index()
        
        self.titles_file_pointer.close()
        self.merge_indexes()
        print(self.page_counter, " pages indexed")
        


if __name__ == "__main__":

    run_directory_path = os.path.abspath(os.getcwd())
    wikipedia_dump_path = sys.argv[1]
    index_path = os.path.join(run_directory_path, sys.argv[2])
    # stats_path = os.path.join(run_directory_path, sys.argv[3])
    # stopword_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stopwords.txt")
    stopword_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stopwords_2.txt")
    
    indexer = Indexer(wikipedia_dump_path, index_directory=index_path, stop_words_file=stopword_path)
    indexer.run()
    
    # merger = MergeIndex(page_count=2000000, index_path=index_path, index_count=6)
    # merger.merge_files()
    # with open(stats_path, "w") as fp:
    #     fp.write(str(total_words) + "\n" + str(num_tokens))
    