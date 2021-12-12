
#1. From XML - Map the identifier to the entry type(name)
import xml.etree.ElementTree as ET
from typing import List

class meshTreeMap:
    """
    Reads and uses mesh hierarchy
    """
    def __init__(self,meshfile,descfile ): #takes mesh tree file as parameter
        self.meshTree = meshfile
        self.meshHierarchy = descfile
        self.entry_to_identifier_map = {}
        self.entry_to_hierarchy_map = {}
        self.hierarchy_to_identifier_map={}
        self.identifier_to_hierarchy_map={}

    def create_entry_to_identifier_map (self):
        """
        Creates an entry_to_identifiers_map with the given mesh hierarchy file.
        """
        tree = ET.parse(self.meshHierarchy)
        root = tree.getroot() #DescriptorRecordSet 
        for desRecord in root: #DescriptorRecord
            for child in desRecord:
                if child.tag == "DescriptorUI":
                    identifier = child.text
                elif child.tag == "DescriptorName":
                    entry_type = child[0].text
                        
                # elif child.tag == "AllowableQualifiersList":   ==> when we want to add subheadings(qualifiers) to give additional context 
                #     for qualifier in child: #qualifier = AllowableQualifier
                #         for qualifierRef in qualifier:
                #             for qualifierProp in qualifierRef:
                #                 if qualifierProp.tag == "QualifierUI":
                #                     #print(qualifierProp.text)
                #                     identifiers.append(qualifierProp.text)
            self.entry_to_identifier_map[entry_type]=identifier
        

    def create_entry_to_hierarchy_map (self): 
        """
        Creates an entry_to_hierarchy_map (1:n)
        """
        with open(self.meshTree, mode='rb') as file: # b is important -> binary
            fileContent = file.read()
        lines = fileContent.decode('UTF-8').split("\n") # each line : entry type;its location in the tree
        for line in lines:
            if len(line) > 0:
                entry = line.split(";")[0]
                loc = line.split(";")[1]
                if entry not in self.entry_to_hierarchy_map:
                    self.entry_to_hierarchy_map[entry]=[]
                self.entry_to_hierarchy_map [entry].append(loc)
        
    def create_hierarchy_to_identifier_map(self):
        """
        Creates a hierarchy_to_identifier_map(1:1) , identifier_to_hierarchy_map(1:n)
        """
        for entry, hierarchy in self.entry_to_hierarchy_map.items():
            identifier =  self.entry_to_identifier_map[entry]
            for hier in hierarchy:
                self.hierarchy_to_identifier_map[hier]= identifier #1:1
            self.identifier_to_hierarchy_map[identifier] = hierarchy #1:n relationship

    def constructMap(self):
        """
        Creates the entry_to_identifiers_map & entry_to_hierarchy_map & hierarchy_to_identifier map
        Will be expected to be called after a class object is created. 
        """
        self.create_entry_to_identifier_map()
        self.create_entry_to_hierarchy_map()
        self.create_hierarchy_to_identifier_map()

    def mapIdentifierToEntry(self,identifier:str) -> str:
        """
        Returns the entry of the chemical given the identifier

        :param identifier: chemcial identifier
        :return: entry of the chemical
        """
        for entry, iden in self.entry_to_identifier_map.items():
            if iden == identifier:
                return entry

    def mapIdentifierToHierarchy(self,identifier:str) -> List[str]:
        """
        Returns the hierarchy of the chemical given the identifier

        :param identifier: chemcial identifier
        :return: a list of the possible hierarchy of a chemical
        """
        return self.identifier_to_hierarchy_map.get(identifier,None)

    def mapEntryToIdentifier(self,entry:str) -> str:
        """
        Returns the identifier of the chemical in a list format given the entry

        :param entry: entry of a chemical
        :return: identifier
        """
        return self.entry_to_identifier_map.get(entry,None)
    
    def mapEntryToHierarchy(self, entry:str) ->List[str]:
        """
        Returns the hierarchy of the chemical in a list format given the entry

        :param entry: entry of a chemical
        :return: hierarchy
        """
        return self.entry_to_hierarchy_map.get(entry,None)

    def mapHierarchyToEntry(self, hierarchy:str) ->str:
        """
        Returns the entry of the chemical in a list format given the hierarchy

        :param hierarchy:hierarchy of a chemical
        :return: entry
        """
        for entry, hi in self.entry_to_hierarchy_map.items():
            if hierarchy==hi:
                return entry
        return None

    def mapHierarchyToIdentifier(self, hierarchy:str) ->str:
        """
        Returns the identifier of the chemical given the hierarchy

        :param hierarchy:hierarchy of a chemical
        :return: identifier
        """
        return self.hierarchy_to_identifier_map.get(hierarchy,None)

    def getParents(self, hierarchy:str) ->List[str]:
        """
        Return the parents of a chemical in a list format, when it is given the hierarchy 

        :param hierarchy: hierarchy of a chemical
        :return: A list of all of the parents identifiers of a chemical
        """
        hierarchy_comp = hierarchy.split(".")
    
        parents_hier = [] #list of the possible parents' hierarchy 
        for i in range(len(hierarchy_comp)-1):
            parent = ".".join(hierarchy_comp[:-(i+1)])
            parents_hier.append(parent)    

        parents =[]
        for hier in parents_hier:
            parents.append(self.mapHierarchyToIdentifier(hier))
        return parents

    def getChildren(self, parentHier:str) ->List[str]:
        """
        Return the children of a chemical in a list format, when it is given the parent's hierarchy

        :param parentHier: hierarchy of a chemical
        :return: A list of all of the children identifiers of a chemical
        """
        parentLen = len(parentHier.split("."))
        children = []
        #search for all of the possible children candidates in the tree
        for hier,identifier in self.hierarchy_to_identifier_map.items():
            if parentHier in hier:
                heirLen = len(hier.split("."))
                if heirLen>parentLen:
                    children.append(identifier)
        children = list(set(children)) #remove the duplicates
        #print(children)
        return children



meshTreeFile = 'mtrees2014.bin'
meshHierFile = 'desc2014.xml'
mt = meshTreeMap(meshTreeFile,meshHierFile)
mt.constructMap()
print(mt.mapHierarchyToIdentifier("D03.438.759.590.138.71"))


