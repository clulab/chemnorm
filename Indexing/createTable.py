import json
import xlsxwriter
from typing import List
from meshTreeMap import meshTreeMap

class createTable:
    """
    A class that creates the data we need for the indexing chemical identification
    """
    def __init__(self,files, mtree, desc): 
        """
        Given the corpus files, creates tables that would we need to create the data

        :param files:corpus files in json format 
        :param mtree:mesh hierarchy file
        :param desc:mesh descriptor file 
        """
        self.jsonData = []
        for file in files:
            f = open(file)
            self.jsonData.append(json.load(f))
        self.treefile = mtree
        self.descfile = desc
        self.mT =meshTreeMap(self.treefile,self.descfile)
        self.mT.constructMap()
        #data we need for the table
        self.appearing_indexing_table={} #key: docid / value: dict format of (identifier that appears in the text, indexing T/F)
        self.non_appearing_indexing={} #key: docid / value: identifiers that does not appear in text but are indexing
        self.indexing_table={}
        self.prefix_table={} #key:docid/value: indexing identifiers prefix of hierarchy 
        self.hier_prefix_table={} #key:identifier/value:prefix of hierarchy 
        self.cnt_table  = {} #key: docid / value: dict format of (identifier,cnt)
        self.ratio_table = {} #key: docid / value: dict format of (identifier,ratio)
        self.child_cnt_table={} #key: docid / value: dict format of (identifier (including the parents), # of child)
        self.child_cnt_norm_table={} #key: docid / value: dict format of (identifier (including the parents), # of child)
        self.child_freq_table={} #key: docid / value: dict format of (identifier (including the parents), # of child)
        self.depth_table={} #key: docid /value: (identifier, depth in meshtree)
        
    
    def write_tables(self):
        """
        Method that fills in the count_table, ratio_tabel, and label_table for each document 
        """
        for data in self.jsonData:
            for document in data['documents']:
                #for each document
                id = document['id']
                is_identifier_indexing={} #key: identifier / value : whether or not if the identifier is an indexing chemical
                non_appearing_indexing=[] #list of indexing chemicals that do not appear in text
                indexing=[]
                identifier_cnt = {} #key: identifier / value: identifier occurrences in this document
                identifier_ratio={} #key: identifier / value: identifier appearance ratio in this document
                total_count = 0 #total count of the identifiers appearing in the document

                #first round : save all of the appearing identifiers of the document 
                for i in range(len(document['passages'])):
                        annotations = document['passages'][i]['annotations']
                        for annotation in annotations:
                            if annotation['infons']['type']=="Chemical" and  len(annotation['locations'])>0: #for appearing identifier in the text
                                identifier = annotation['infons']['identifier']
                                if identifier!="-":
                                    if "," in identifier:
                                        identifiers = identifier.split(",")
                                    if "|" in identifier:
                                        identifiers = identifier.split("|")
                                    else:
                                        identifiers = identifier.split(",")
                                    for iden in identifiers:
                                        iden = iden.strip("MESH:")
                                        is_identifier_indexing[iden] = 0
                                        if iden not in identifier_cnt:
                                            identifier_cnt[iden]= 1
                                        else:
                                            identifier_cnt[iden]+=1
                                        total_count += len(annotation['locations'])  #for each of the identifier, add the occurrence of it 
                                        
                
                #second round : now check if those appearing chemicals are indexing or not
                for i in range(len(document['passages'])):  
                    annotations = document['passages'][i]['annotations']
                    for annotation in annotations:
                        if annotation['infons']['type'] == "MeSH_Indexing_Chemical":
                            identifier = annotation['infons']['identifier'].strip("MESH:")
                            if identifier!="-":
                                identifiers = identifier.split(",")
                                for iden in identifiers:
                                    iden = iden.strip("MESH:")
                                    indexing.append(iden)
                                    if iden in is_identifier_indexing: #the indexing chemical  appears in text
                                        is_identifier_indexing[identifier] = 1
                                    else: #indexing chemical that does not appear in thext 
                                        non_appearing_indexing.append(iden)
                                        

                for identifier in is_identifier_indexing:
                    identifier_ratio[identifier] = identifier_cnt[identifier]/total_count
        

                # #debugging
                # print(id)
                # print(identifier_cnt)
                # print(identifier_ratio)
                # print(is_identifier_indexing)
                self.cnt_table[id]=identifier_cnt
                self.ratio_table[id] = identifier_ratio
                self.appearing_indexing_table[id]=is_identifier_indexing
                self.non_appearing_indexing[id]=non_appearing_indexing
                self.indexing_table[id]=indexing
            
    def write_prefix_table(self):
        """
        Writes the prefix table for the prefix feature
        Given the indexing chemicals of each document, gets its prefix
        """
        if len(self.indexing_table)==0:
            self.write_tables() #read corpus
        # converts the indexing chemical into the hierarchy prefix
        for docid, chemicals in self.indexing_table.items():
            #print(chemicals)
            prefixes =[]
            for chem in chemicals:
                hier = self.mT.mapIdentifierToHierarchy(chem)
                if  hier is not None:
                    prefixes.extend(hier)
            prefixes=list(set([x[:7] for x in prefixes]))
            self.prefix_table[docid]=prefixes
        #print(self.prefix_table)
    
    def write_child_cnt_table(self):
        """
        1. Add the parents of the appearing chemicals
        2. Get the child count of each chemicals
        """
        if len(self.appearing_indexing_table)==0:
            self.write_tables()

        #add parent rows 
        for docid, indexing in self.appearing_indexing_table.items():
            child_cnt_dict={} #key: identifier, value: count 
            child_cnt_norm={}
            child_freq={}
            #fill in the rows 
            for identifier in indexing:
                #for each appearing identifier
                child_cnt_dict[identifier]=0
                hierarchy= self.mT.mapIdentifierToHierarchy(identifier)
                if hierarchy is not None: # if it does have a mesh hierarchy
                    for hier in hierarchy:
                        parents = self.mT.getParents(hier) #adding additional rows (parents)
                        for parent in parents:
                            child_cnt_dict[parent]=0

                        
            #get the child count feature (the count of children in the article) for the chemicals 
            for identifier in child_cnt_dict:
                hierarchy= self.mT.mapIdentifierToHierarchy(identifier)
                childrens_added = []
                if hierarchy is not None: # if the identifier has a hierarchy
                    for hier in hierarchy: #for all the possible hierarchy of this identifier
                        children = self.mT.getChildren(hier) #get all of its children
                        for child in children: 
                            #if the child appeared in this document and we didnt count this children yet
                            if child in self.appearing_indexing_table[docid] and child not in childrens_added:  
                                child_cnt_dict[identifier]+=self.cnt_table[docid][child] #add how many times this child appeared in the article
                                childrens_added.append(child)
                    #calculated the number of children of this chemical
                    # now, calculate the frequency of this chemical's children
                    if len(childrens_added)==0:
                        child_freq[identifier]=0
                    else:
                        child_freq[identifier]=float(len(childrens_added))/child_cnt_dict[identifier]
                else:#this chemical does not have a hierarhcy
                    child_cnt_dict[identifier]=0 
                    child_freq[identifier]=0
            #get the ratio of child count by dividing it to the number of chemicals that appear in the article
            total_cnt = 0
            for child in self.cnt_table[docid]:
                total_cnt += self.cnt_table[docid][child] 
               
            for identifier in child_cnt_dict:
                if child_cnt_dict[identifier] == 0:
                    child_cnt_norm[identifier] = 0
                else:
                    child_cnt_norm[identifier] = float(child_cnt_dict[identifier]) / total_cnt# of chemicals that appear in text
            
            #write it back
            self.child_cnt_table[docid] = child_cnt_dict
            self.child_cnt_norm_table[docid] = child_cnt_norm
            self.child_freq_table[docid]=child_freq

    def write_hier_prefix_table(self):
        """
        Writes hierarchy_prefix table.
        Saves the readed identifiers (appeared+parent rows) and map those chemicals to its hierarchy prefix
        """
        if len(self.child_cnt_table)==0:
            self.write_child_cnt_table()
       
        for _,chemicals in self.child_cnt_table.items():
            for chemical in chemicals:
                hier = self.mT.mapIdentifierToHierarchy(chemical)
                if hier is not None:
                    hier = list(set([x[:7] for x in hier]))
                self.hier_prefix_table[chemical]=hier
        #print(self.hier_prefix_table)
            
       
    def write_to_file_wo_child_cnt(self,filename):
        """
        Create data without considering the mesh hierarchy.
        Does not add children count as a feature
        """
        self.wb = xlsxwriter.Workbook(filename)
        self.ws = self.wb.add_worksheet('Sheet 1')
        self.ws.write(0,0,"DocID")
        self.ws.write(0,1,"Chemical")
        self.ws.write(0,2,"Number of Occurrences")
        self.ws.write(0,3,"Ratio")
        self.ws.write(0,4,"Indexing(T/F)")
        rowidx = 1
        for docid in self.appearing_indexing_table:
            for identifier, is_indexing in self.appearing_indexing_table[docid].items():
                self.ws.write(rowidx,0,docid)
                self.ws.write(rowidx,1,identifier)
                if identifier not in self.cnt_table[docid]:
                    self.ws.write(rowidx,2,0)
                    self.ws.write(rowidx,3,0)
                else:
                    self.ws.write(rowidx,2,self.cnt_table[docid][identifier])
                    self.ws.write(rowidx,3,self.ratio_table[docid][identifier])
                self.ws.write(rowidx,4,is_indexing)
                rowidx = rowidx+1
        self.wb.close()

    def write_to_file_w_child_cnt(self,filename):
        """
        Create data with consideration of the mesh hierarchy
        1. Adds parents of the appearing chemicals as new rows to the table
        2. Adds child count as a new feature 
        *Note: write_child_cnt_table must be called before

        :param filename: the excel sheet file to save the result
        """
        
        self.write_tables()
        self.write_child_cnt_table()
        self.write_prefix_table()
        self.write_hier_prefix_table()
        #check
        #print(self.appearing_indexing_table)
        # print(self.child_cnt_table)
        # print(self.non_appearing_indexing)
        # print(self.ratio_table)
        # print(self.depth_table)

        self.wb = xlsxwriter.Workbook(filename)
        self.ws = self.wb.add_worksheet('Sheet 1')
        self.ws.write(0,0,"DocID")
        self.ws.write(0,1,"Chemical")
        self.ws.write(0,2,"Number of Occurrences")
        self.ws.write(0,3,"Ratio")
        self.ws.write(0,4,"Child occurrences")
        self.ws.write(0,5,"Child count normalized")
        self.ws.write(0,6,"Child Frequency") #among all of the chemicals that appeared in the text, the freqeuncy of the child
        self.ws.write(0,7,"Appeared") #whether or not it appeared in the text
        self.ws.write(0,8,"Hierarchy") #hierarchy of the chemical
        self.ws.write(0,9,"IsPrefix") #whether or not it is a prefix of the indexing chemical of the document
        self.ws.write(0,10,"Indexing(T/F)")
        rowidx = 1

        for docid, chemicals in self.child_cnt_table.items():
            for identifier, childCount in chemicals.items():
                self.ws.write(rowidx,0,docid)
                self.ws.write(rowidx,1,identifier)
                isIndexing = 0 
                if identifier in self.cnt_table[docid]: #for document appearing chemicals
                    self.ws.write(rowidx,2,self.cnt_table[docid][identifier])
                    self.ws.write(rowidx,3,self.ratio_table[docid][identifier])
                    self.ws.write(rowidx,4,childCount)
                    self.ws.write(rowidx,5,self.child_cnt_norm_table[docid][identifier])
                    self.ws.write(rowidx,6,self.child_freq_table[docid][identifier])
                    self.ws.write(rowidx,7,1) #appear in the text
                
                    isIndexing = self.appearing_indexing_table[docid][identifier]
                else: #was added as an additional row(does not appear in the text) 
                    self.ws.write(rowidx,2,0)
                    self.ws.write(rowidx,3,0)
                    self.ws.write(rowidx,4,childCount)
                    self.ws.write(rowidx,5,self.child_cnt_norm_table[docid][identifier])
                    self.ws.write(rowidx,6,self.child_freq_table[docid][identifier])
                    self.ws.write(rowidx,7,0) #did not appear in the text
                    if identifier in self.non_appearing_indexing[docid]: #it is an indexing chemical
                        isIndexing = 1

                #hierarchy of this chemical
                prefix = 0
                hierarchy = self.mT.mapIdentifierToHierarchy(identifier)
                
                if hierarchy is not None:
                    
                    #check if it is a prefix of the indexing chemical of this document
                    #self.ws.write(rowidx,8,",".join(hierarchy)) #selects the hierarchy that has the shared prefix with the indexing chemical
                    prefixed_hierarchy = [x[:7] for x in hierarchy]
                    self.ws.write(rowidx,8,prefixed_hierarchy[0]) #select only one random element of the prefixed hierarhcy
                    for hier in hierarchy:
                        for indexing_prefix in self.prefix_table[docid]: #indexing prefix of this certain document
                            if indexing_prefix == hier[0:7]:
                                prefix=1
                                break
                                #in the future, if an identifier has several hierarchies -- it will go through all of it
                else:
                    self.ws.write(rowidx,8,"None")
                self.ws.write(rowidx,9,prefix)
                
                self.ws.write(rowidx,10,isIndexing)
                rowidx+=1
        self.wb.close()

    def write_prefix_file(self,filename):
      
        """
        Create data with consideration of the mesh hierarchy
        1. Adds parents of the appearing chemicals as new rows to the table
        2. Adds child count as a new feature 
        *Note: write_child_cnt_table must be called before

        :param filename: the excel sheet file to save the result
        """
        
        self.write_tables()
        self.write_child_cnt_table()
        self.write_prefix_table()
        self.write_hier_prefix_table()
   

        self.wb = xlsxwriter.Workbook(filename)
        self.ws = self.wb.add_worksheet('Sheet 1')
        self.ws.write(0,0,"Prefix")#prefix of the hierarchy 
        self.ws.write(0,1,"IsPrefix") #whether or not it is a prefix of the indexing chemical of the document
 
        rowidx = 1

        for docid, chemicals in self.child_cnt_table.items():
            for identifier, _ in chemicals.items():
           
                #hierarchy of this chemical
                prefix = 0
                hierarchy = self.mT.mapIdentifierToHierarchy(identifier)
                
                if hierarchy is not None:
                    print(hierarchy)
                    #check if it is a prefix of the indexing chemical of this document
                    for hier in hierarchy:
                    
                        #check for all of the indexing chemicals of this document, if it shares the prefix
                        for indexing_prefix in self.prefix_table[docid]: #indexing prefix of this document
                            if indexing_prefix == hier:
                                prefix=1
                                self.ws.write(rowidx,0,hier)
                                self.ws.write(rowidx,1,prefix) #is prefix
                            else:
                                self.ws.write(rowidx,0,hier)
                                self.ws.write(rowidx,1,prefix) #it is not a prefix
                            rowidx+=1
                else:
                    self.ws.write(rowidx,0,"None")
                    self.ws.write(rowidx,1,prefix)
                    rowidx+=1       
        self.wb.close()

    def check_depth_with_indexing(self,filename):
        """
        Create a table that sees the relationship with the identifier's depth and the indexing 
        Each row would be (identifier, mesh depth, indexing (T/F))
        """
        self.write_tables()
        self.write_child_cnt_table()
     
        self.wb = xlsxwriter.Workbook(filename)
        self.ws = self.wb.add_worksheet('Sheet 1')
        self.ws.write(0,0,"Chemical")
        self.ws.write(0,1,"Depth")
        self.ws.write(0,2,"Indexing(T/F)")
        rowidx = 1

        for docid, chemicals in self.child_cnt_table.items():
            for identifier, indexing in chemicals.items():
                hierarchy = self.mT.mapIdentifierToHierarchy(identifier)
                print(hierarchy)
                if hierarchy is not None: 
                    #for all of the possible hierarchy 
                    depths = []
                    for hier in hierarchy:
                        self.ws.write(rowidx,0,identifier)
                        depth = len(hier.split("."))
                        if depth not in depths:
                            depths.append(str(depth))
                    self.ws.write(rowidx,1,",".join(depths))
                    if identifier in self.cnt_table[docid]: #appeared in article
                        self.ws.write(rowidx,2,self.appearing_indexing_table[docid][identifier])
                    else:#for added chemicals as parents
                        if identifier in self.non_appearing_indexing[docid]: #it is an indexing chemical
                            self.ws.write(rowidx,2,1)
                        else:
                            self.ws.write(rowidx,2,0)
                   
                else: #this chemical does not have a hierarchy
                    self.ws.write(rowidx,0,identifier)
                    self.ws.write(rowidx,1,0) #depth 0 
                    if identifier in self.cnt_table[docid]: #text appearing chemicals 
                        self.ws.write(rowidx,2,indexing)
                    else:#for added chemicals as parents
                        if identifier in self.non_appearing_indexing[docid]: #it is an indexing chemical
                            self.ws.write(rowidx,2,1)
                        else:
                            self.ws.write(rowidx,2,0)
                rowidx+=1
                    
                
        self.wb.close()
        

# get data from two corpora
#filenames = ['BC7T2-CDR-corpus-dev.BioC.json']
filenames=['BC7T2-NLMChem-corpus-dev.BioC.json']
#cT = createTable(filenames,'mtrees2014.bin','desc2014.xml')
cT = createTable(filenames,'mtrees2021.bin','desc2021.xml')
cT.write_to_file_w_child_cnt('prefixed_dev_nlm_table.xlsx')
#cT.check_depth_with_indexing('nlm_depth.xlsx')

