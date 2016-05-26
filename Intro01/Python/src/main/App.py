import csv, ast, base64, itertools, os, getopt, sys, json, raptureAPI
from collections import OrderedDict

rapture = None
UPLOAD, BLOBTODOC, DOCTOSERIES, ALL = range(4)

def retrieveParams():
	hasErrors = False
	errors = []
	host, user, password, file_location, step = "", "", "", "", ""

	# Retrieve flags
	try:
		opts, args = getopt.getopt(sys.argv[1:], 'h:u:p:f:s:', ["host=", "user=", "password=", "file=", "help", "step="])
	except getopt.GetoptError:
		print 'demoPython.py -h <host> -u <user> -p <password> -f <csv_file_location> -s <demo_step>'
		sys.exit(2)

	# Set params according to flags
	for opt, arg in opts:
		if opt == 'help':
			print 'demoPython.py -h <host> -u <user> -p <password> -f <csv_file_location> -s <demo_step>'
			sys.exit()
	  	elif opt in ("-h", "--host"):
	  		host = arg
	  	elif opt in ("-u", "--user"):
	  		user = arg
	  	elif opt in ("-p", "--password"):
	  		password = arg
	  	elif opt in ("-f", "--file"):
	  		file_location = arg
	  	elif opt in ("-s", "--step"):
	  		step = arg

	# Check if params are set after flags
	if not host:
		try:
			host = os.environ.get('RAPTURE_HOST')
		except:
			hasErrors = True
			errors.append("No Rapture host specified. Please set the environment variable RAPTURE_HOST or supply the -h option on the command line.")
	if not user:
		try:
			user = os.environ.get('RAPTURE_USER')
		except:
			hasErrors = True
			errors.append("No Rapture user specified. Please set the environment variable RAPTURE_USER or supply the -u option on the command line.")
	if not password:
		try:
			password = os.environ.get('RAPTURE_PASSWORD')
		except:
			hasErrors = True
			errors.append("No Rapture password specified. Please set the environment variable RAPTURE_PASSWORD or supply the -p option on the command line.")
	if not file_location:
		try:
			file_location = os.environ.get('RAPTURE_TUTORIAL_CSV')
		except:
			hasErrors = True
			errors.append("No CSV specified. Please set the environment variable RAPTURE_TUTORIAL_CSV or supply the -f option on the command line.")
	if not step:
		hasErrors = True
		errors.append("No demo step specified. Please supply the -s option on the command line.")

	# Check if params are set after the environment variables step
	if not host:
		hasErrors = True
		errors.append("No Rapture host specified. Please set the environment variable RAPTURE_HOST or supply the -h option on the command line.")
	if not user:
		hasErrors = True
		errors.append("No Rapture user specified. Please set the environment variable RAPTURE_USER or supply the -u option on the command line.")
	if not password:
		hasErrors = True
		errors.append("No Rapture password specified. Please set the environment variable RAPTURE_PASSWORD or supply the -p option on the command line.")
	if not file_location:
		hasErrors = True
		errors.append("No CSV specified. Please set the environment variable RAPTURE_TUTORIAL_CSV or supply the -f option on the command line.")

	# If errors exist, print all errors and exit, else return params
	if hasErrors:
		for error in errors:
			print error
		sys.exit(1)
	else:
		step = step.lower()
		if step == "upload":
			step = UPLOAD
		elif step == "blobtodoc":
			step = BLOBTODOC
		elif step == "doctoseries":
			step = DOCTOSERIES
		elif step == "all":
			step = ALL

		return host, user, password, file_location, step

def loginToRapture(url, username, password):
	global rapture

	rapture = raptureAPI.raptureAPI(url, username, password)
	if 'valid' in rapture.context and rapture.context['valid']:
	    print 'Logged in successfully ' + url
	else:
		print "Login unsuccessful"

def upload(file_location):
	global rapture

	# Import csv file
	with open(file_location, 'rb') as csvFile:
		print "Reading CSV from file "+file_location

		rawFileData = csvFile.read()

	# Create blob repo
	blobRepoUri = "blob://tutorialBlob"
	rawCsvUri = blobRepoUri + "/introDataInbound.csv"
	config = "BLOB {} USING MONGODB {prefix=\"tutorialBlob\"}"
	metaConfig = "REP {} USING MONGODB {prefix=\"tutorialBlob\"}"
	if(rapture.doBlob_BlobRepoExists(blobRepoUri)):
		print "Repo exists, cleaning & remaking"
		rapture.doBlob_DeleteBlobRepo(blobRepoUri)
	rapture.doBlob_CreateBlobRepo(blobRepoUri, config, metaConfig)

	# Encode and Store Blob
	print "Uploading CSV"
	encoded_blob = base64.b64encode(str(rawFileData))
	rapture.doBlob_PutBlob(rawCsvUri, encoded_blob, "text/csv")

	print "CSV successfully uploaded to "+rawCsvUri

def blobToDoc():
	global rapture

	blobUri = "blob://tutorialBlob/introDataInbound.csv"

	# Check that blob exists
	if rapture.doBlob_BlobExists(blobUri):

		# Pull encoded blob out of rapture
	 	encoded_blob = rapture.doBlob_GetBlob(blobUri)['content']
		# Decode blob using base64 python library
		blob_string = base64.b64decode(str(encoded_blob))
		# Add list identifiers to string so that we can convert to python list
		blob_string = "[[\"" + blob_string.replace(',', "\",\"").replace('\n', "\"],[\"") + "\"]]"
		# Convert string to python list
		rows = ast.literal_eval(blob_string)
		# Create doc repo
		docRepoUri = "//tutorialDoc"
		docUri = docRepoUri + "/introDataTranslated"
		config = "NREP {} USING MONGODB {prefix=\"tutorialDoc\"}"
		if(rapture.doDoc_DocRepoExists(docRepoUri)):
			rapture.doDoc_DeleteDocRepo(docRepoUri)
		rapture.doDoc_CreateDocRepo(docRepoUri, config)

		#CREATE ONE FLAT JSON
		#CREATING INITIAL STRUCTURE
		keys = rows[0]
		rowData = {}
		docIndex = 0
		blobData = list()
		# Skip the first frow since it contains the keys, & skip last row because it is an empty line
		for row in rows[1:-1]:
			rowData = {keys[0]:row[0],keys[1]:row[1],keys[2]:row[2],keys[3]:row[3],keys[4]:row[4],keys[5]:row[5]}
			blobData.append(rowData)
		#This is the top level of json/dict that we will be inserting
		Order = OrderedDict()
		for entry in blobData:
			Order['series_type'] = entry['series_type']
			Order['frequency'] = entry['frequency']
			Order['index_id'] = {}
		index_id = list()
		#Add index_id's to the master json/dict
		for x in blobData:
			index_id.append(x['index_id'])
		index_idSet = set(index_id)
		index_idDict = {}
		for x in index_idSet:
			index_idDict.update({x:{}})
		Order['index_id'] = index_idDict
		priceTypeList = list()
		for x in blobData:
			priceTypeList.append(x['price_type'])
		priceTypeSet = set(priceTypeList)
		priceTypeDict = {}
		for x in priceTypeSet:
			priceTypeDict.update({x:{}})
		indxID = Order['index_id']
		indx_idUpdate = {}
		#Add price_types to the master json/dict
		for x in indxID:
			indx_idUpdate.update({x:priceTypeDict})
		Order['index_id'] = indx_idUpdate

		#Add date:price to correct index_id & price_type
		for index_id in Order['index_id']:
			#Use disposable dict to reset data for each index_id
			disposableDict = {}
			for item in blobData:
				if item['index_id'] == index_id:
					type = item['price_type']
					date = item['date']
					price = item['index_price']
					disposableDict.update({type:{}})
			for item in blobData:
				if item['index_id'] == index_id:
					for x in disposableDict:
						if item['price_type'] == x:
							disposableDict[x].update({item['date']:float(item['index_price'])})
			Order['index_id'][index_id] = disposableDict


		#PUT THE CSV DATA RETRIEVED FROM A BLOB & TRANSLATED INTO THE DOCUMENT REPOSITORY
		rapture.doDoc_PutDoc(docUri, json.dumps(Order, sort_keys=False))
		print "Successfully translated blob to docs"
	else:
		print "Please make sure that blob repo and blob are uploaded already"

def docToSeries():
	global rapture
	docRepoUri = "//tutorialDoc"

	# Check that docs exists and retrieve them
	docUri = docRepoUri + "/introDataTranslated"
	seriesRepoUri = "series://datacapture"
	check = rapture.doDoc_DocExists(docUri)
	try:
		assert check == True
	except:
		print "Error: document "+docUri+" does not exist. Please create the document from the blob first."

	docContent = ast.literal_eval(rapture.doDoc_GetDoc(docUri))

	# Check if datacapture repo exists
	if rapture.doSeries_SeriesRepoExists(seriesRepoUri):
		# Retrieve document
		print "Adding price data from "+docUri+" to series repo "+seriesRepoUri
		# Convert json string to a python dict object
		doc = ast.literal_eval(rapture.doDoc_GetDoc(docUri))
		# Generate specific URI's based on data points
		seriesUri = seriesRepoUri + "/"
		seriesUri = seriesUri + str(doc['series_type']) + "/"
		seriesUri = seriesUri + "TutorialIntro_Python/"
		disposableUri = seriesUri
		for x in doc['index_id']:
			#Reset base URI's so that one long URI is not created
			seriesUri = disposableUri
			seriesUri = seriesUri + str(x) +"/"
			tailoredSeriesUri = seriesUri
			for priceType in doc['index_id'][x]:
				#Reset base URI's so that one long URI is not created
				seriesUri = tailoredSeriesUri
				seriesUri = seriesUri + str(doc['frequency']) + "/"
				seriesUri = seriesUri + str(priceType)
				for date in doc['index_id'][x][priceType].keys():
					print "Adding price data to series: " + seriesUri
					for price in doc['index_id'][x][priceType].values():
						# Store each date and price in the appropriate series
						rapture.doSeries_AddDoubleToSeries(seriesUri, date, float(price))


		print "Successfully updated series"
	else:
		print "Please make sure that demoData plugin is installed"


def startDemo():
	host, user, password, file_location, step = retrieveParams()
	loginToRapture(host, user, password)

	if step == UPLOAD:
		upload(file_location)
	elif step == BLOBTODOC:
		blobToDoc()
	elif step == DOCTOSERIES:
		docToSeries()
	elif step == ALL:
		upload(file_location)
		blobToDoc()
		docToSeries()

	print "Demo Completed"
	print

print
startDemo()
