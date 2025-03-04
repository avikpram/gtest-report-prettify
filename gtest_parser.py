import json
import sys, os
from jinja2 import FileSystemLoader, Environment
import xml.etree.ElementTree as ET
from junitparser import *

# Constants
TEMPLATE_FILE = "gtest_template.html"
OUTPUT_FILE = "gtest_output.html"

def process_input(input_file, disabled_num=0):
    """ Processes the input file.
        Will return a JSON object to be used by the HTML parser.
        If the file is in XML format it will be turned into a JSON object.
    """

    data = None

    with open(input_file) as gtest_json:
        if input_file.endswith('.json'):
            data = json.load(gtest_json)
        elif input_file.endswith('.xml'):
            # Need to turn the XML into the same format as the JSON
            data = process_xml(gtest_json, disabled_num)
        else:
            print("ERROR: Unknown file type.")
            sys.exit()

    return data

def process_xml(xml, disabled_num=0):
    """ Processes the XML file.
        Will return a JSON object that matches that created by GTEST.
    """

    tree = ET.parse(xml)
    root = tree.getroot()
    overviewName = root.attrib['name']
    if overviewName.startswith("GTestClass_"):
      overviewName = overviewName[11:] 
      
    overviewTests = int(root.attrib['tests'])
    overviewFailed = int(root.attrib['failures'])

    #
    # TODO Read 'disabled' status to xml directly
    # Currently total-disabled number is passed separately
    #
        
    overviewDisabled = disabled_num # int(root.attrib['disabled'])
    data = {
        'name': overviewName,
        'tests': overviewTests,
        'failures': overviewFailed,
		    'disabled': overviewDisabled,
        'testsuites': []
    }

    for child in root:
        testSuitename = child.attrib['name']
        if testSuitename.startswith("GTestClass_"):
          testSuitename = testSuitename[11:]         
        totalTests = int(child.attrib['tests'])
        failed = int(child.attrib['failures'])
        disabled = int(child.attrib['disabled'])

        tempTest = []
        for test in child:
            testName = test.attrib['name']
            testTime = test.attrib['time']
            testStatus = test.attrib['status'].upper()
            # Getting all of the failure messages
            testFailures = []
            for failure in test:
                testFailure = failure.attrib['message']
                testFailures.append({
                    'failure': testFailure
                })

            # If there are no failures dont add it to the JSON
            if testFailures:
                tempTest.append({
                    'name': testName,
                    'time': testTime,
                    'status': testStatus,
                    'failures': testFailures
                })
            else:
                tempTest.append({
                    'name': testName,
                    'status': testStatus,
                    'time': testTime
                })
        
        # print(tempTest)
        for t in tempTest:
          print testSuitename+"."+t['name']+": "+t['status']
          
        print "> "+str(totalTests)+", "+str(failed)+", "+str(disabled)
        print "------------------"
        
        tempTestSuite = {
            'name': testSuitename,
            'tests': totalTests,
            'failures': failed,
            'disabled': disabled,
            'testsuite': tempTest
        }
        data['testsuites'].append(tempTestSuite)

    return data

def create_html(data):
    """ Turns the JSON object into a HTML file.
        Will grab the template and render it with our JSON object.
    """
    templateLoader = FileSystemLoader(searchpath="./template/")
    templateEnv = Environment(loader=templateLoader)
    template = templateEnv.get_template(TEMPLATE_FILE)
    
    with open(os.path.join('.', OUTPUT_FILE), "w") as output_html:
        output_html.write(template.render(test_overview=data, test_suites=data['testsuites']))
        
    print "...\nTest report available at: "+str(os.path.join('.', OUTPUT_FILE))

if __name__ == "__main__":
    if len(sys.argv) < 2:
      print "\nERROR: No input path or file provided\n"
      sys.exit()

    if os.path.isdir(sys.argv[1]):
        input_path = sys.argv[1]
        print "\nCombine all available XML files and process\n...\n"
        
        try:
            os.remove(os.path.join(input_path, 'temp', 'merged.xml'))
        except OSError:
            pass
    
        xml_list = []
        mergedXml = JUnitXml()
        test_num = 0
        fail_num = 0
        disable_num = 0
      
        for f in os.listdir(input_path):
          if f.endswith(".xml"):
            xml_list.append(os.path.join(input_path, f))
            
        for f in xml_list:
          # extract disabled test statistic
          suite = JUnitXml.fromfile(f)._elem.findall('testsuite')[0]
          suite.attrib['skipped'] = suite.attrib['disabled']
          
          # accumulate disabled test statistic
          disable_num += int(suite.attrib['skipped'])
          
          # merge XML
          mergedXml = mergedXml + JUnitXml.fromfile(f)
            
        mergedXml.name = 'AllTests'
        mergedXml.update_statistics()

        #
        # TODO Add 'disabled' status to XML directly
        # Currently total-disabled number is passed separately
        #
        
        if not os.path.exists(os.path.join(input_path, 'temp')):
          os.makedirs(os.path.join(input_path, 'temp'))
    
        mergedXml.write(os.path.join(input_path, 'temp', 'merged.xml'))
        json_data = process_input(os.path.join(input_path, 'temp', 'merged.xml'), disable_num)
        
    elif os.path.isfile(sys.argv[1]):
        print "\nProcess single XML/JSON file\n...\n"
        json_data = process_input(sys.argv[1])
        
    else:
        print "\nERROR: Incorrect path or filename provided\n"
        sys.exit()
        
    create_html(json_data)
