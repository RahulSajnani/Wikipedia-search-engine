import re, os, linecache
import heapq

global categories
categories = sorted(["references", "body", "infobox", "title", "category", "links"])

def read_token_line(line):

    words = line.split()
    if len(words) == 0:
        return None
    token_pair = (words[0], [])
    for i in range(1, len(words)):
        token_pair[1].append(int(words[i]))
    return token_pair


def merge_postings_list(postings_dict, postings_dict_2):
    '''
    Merge two posting's list 
    '''

    combined_postings_list = {}

    for field in categories:
        
        doc_id_list = []
        
        if postings_dict.get(field) is None:
            postings_dict[field] = {"postings_list": []}
        
        if postings_dict_2.get(field) is None:
            postings_dict_2[field] = {"postings_list": []}

        postings_list_1 = postings_dict[field]["postings_list"]
        postings_list_2 = postings_dict_2[field]["postings_list"]

        if len(postings_dict[field]["postings_list"]) > 0 and len(postings_dict_2[field]["postings_list"]) > 0:           
            
            
            ptr_1 = 0
            ptr_2 = 0

            while ((ptr_1 < len(postings_list_1)) and (ptr_2 < len(postings_list_2))):
                
                if postings_list_1[ptr_1][0] > postings_list_2[ptr_2][0]:
                    doc_id_list.append(postings_list_2[ptr_2])
                    ptr_2 += 1


                elif postings_list_1[ptr_1][0] < postings_list_2[ptr_2][0]:
                    doc_id_list.append(postings_list_1[ptr_1])
                    ptr_1 += 1

                else:
                    # Doc ids are same 
                    avg_doc_count = (postings_list_1[ptr_1][1] + postings_list_2[ptr_2][1])
                    doc_id_list.append((postings_list_1[ptr_1][0], avg_doc_count))
                    ptr_1 += 1
                    ptr_2 += 1

            while ((ptr_1 < len(postings_list_1))):
                
                doc_id_list.append(postings_list_1[ptr_1])
                ptr_1 += 1

            while ((ptr_2 < len(postings_list_2))):

                doc_id_list.append(postings_list_2[ptr_2])
                ptr_2 += 1

        elif len(postings_list_1) > 0:
            doc_id_list = postings_list_1 

        else: 
            doc_id_list = postings_list_2

        # print(len(doc_id_list), len(postings_list_1), len(postings_list_2))
        combined_postings_list[field] = {"postings_list": doc_id_list} 

    return combined_postings_list

def pop_token(heap, file_pointers):
    '''
    '''
    token_pair = heapq.heappop(heap)
    fp = file_pointers[token_pair[1][-1]]

    read_token = read_token_line(fp.readline())
    if read_token is not None:
        read_token[1].append(token_pair[1][-1])
        heapq.heappush(heap, read_token)
    else:
        fp.close()

    return token_pair

def decode_line(line):
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

def get_all_postings_list(token_pair, files_dictionary):

    token_dictionary = {}
    for field in categories:
        if files_dictionary.get(field) is not None:
            if token_pair[1][categories.index(field)] != 0:
                file_name = files_dictionary[field][token_pair[1][-1]]
                line = linecache.getline(file_name, int(token_pair[1][categories.index(field)]))
                token_dictionary[field] = decode_line(line)
            else:
                token_dictionary[field] = {"postings_list": []}

        else:
            token_dictionary[field] = {"postings_list": []}

    return token_dictionary

def merge_files(files_dictionary, k = 4):
    
    
    token_files = files_dictionary["tokens"]
    file_pointers = []
    tokens_heap = []
    del(files_dictionary["tokens"])
    
    for token_file_name in token_files:
        fp = open(token_file_name, "r")
        token_pair = read_token_line(fp.readline())
        file_pointers.append(fp)
        if token_pair:
            token_pair[1].append(len(file_pointers) - 1)
        heapq.heappush(tokens_heap, token_pair)
        
    while len(tokens_heap) > 0:
        
        token_pair = pop_token(tokens_heap, file_pointers)
        posting_dict = get_all_postings_list(token_pair, files_dictionary)
        print(posting_dict)
        # print(token_pair[0])
        if len(tokens_heap):
            while token_pair[0] == tokens_heap[0][0]:
                token_pair_2 = pop_token(tokens_heap, file_pointers)
                posting_dict_2 = get_all_postings_list(token_pair_2, files_dictionary)
                posting_dict = merge_postings_list(posting_dict, posting_dict_2)
                
    print("end")


if __name__=="__main__":

    files_dictionary = {"tokens": ["tokens_0.txt", "tokens_1.txt", "tokens_2.txt"], "body": ["index_body_0.txt", "index_body_1.txt", "index_body_2.txt"]}
    for field in files_dictionary:
        for i in range(len(files_dictionary[field])):
            files_dictionary[field][i] = os.path.join("./search_index/", files_dictionary[field][i])
    merge_files(files_dictionary)
    pass