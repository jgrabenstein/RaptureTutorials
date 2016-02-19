package rapture.tutorial;

import java.io.BufferedReader;
import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.TreeMap;
import java.util.zip.DataFormatException;

import rapture.common.BlobContainer;
import rapture.common.RaptureURI;
import rapture.common.Scheme;
import rapture.common.client.HttpBlobApi;
import rapture.common.client.HttpDocApi;
import rapture.common.client.HttpLoginApi;
import rapture.common.client.HttpSeriesApi;
import rapture.common.client.ScriptClient;
import rapture.common.client.SimpleCredentialsProvider;
import rapture.common.impl.jackson.JacksonUtil;

public class App {
	private ScriptClient client;
	private HttpLoginApi loginApi;
	private HttpBlobApi blobApi;
	private HttpDocApi docApi;
	private HttpSeriesApi seriesApi;

	private static final String SERIES_AUTHORITY = "datacapture";
	private static final String BLOB_AUTHORITY = "tutorialBlob";
	private static final String DOC_AUTHORITY = "tutorialDoc";

	private String blobRepoUri;
	private String docRepoUri;
	private String rawCsvUri;
	private String jsonDocumentUri;

	private static final String SERIES_TYPE_HEADER = "series_type";
	private static final String FREQUENCY_HEADER = "frequency";
	private static final String INDEX_ID_HEADER = "index_id";
	private static final int SERIES_TYPE_INDEX = 0;
	private static final int INDEX_ID_INDEX = 1;
	private static final int FREQUENCY_INDEX = 2;
	private static final int PRICE_TYPE_INDEX = 3;
	private static final int DATE_INDEX = 4;

	public static final void main(String args[]) {
		App tutorialApp = new App();

		// This helper class "hides" the code to work out how to connect to the Rapture environment
		// i.e. the host, username and password. It also determines what aspect of the tutorial is
		// to be run.
		TutorialHelper.parseOptions(args);

		tutorialApp.init();

		tutorialApp.runTutorial();
	}

	private void init() {
		System.out.println("Starting up..");
		System.out.println("Logging in to " + TutorialHelper.getHost());

		// The Rapture login API requires a credentials provider (an interface). SimpleCredentialsProvider
		// is a way of providing the username and password in code. Alternative implementations could prompt
		// for a username and password via a UI.
		SimpleCredentialsProvider creds = new SimpleCredentialsProvider(TutorialHelper.getUserName(),
				new String(TutorialHelper.getPassword()));

		// Here is where we connect to the Rapture environment
		// If the login process fails we will throw an exception.
		loginApi = new HttpLoginApi(TutorialHelper.getHost(), creds);
		loginApi.login();

		// The ScriptClient class is a convenient way to wrap up a logged in environment
		// the api objects hanging off script client will use the same credentials already
		// verified with a Rapture instance.
		client = new ScriptClient(loginApi);

		blobApi = client.getBlob();
		docApi = client.getDoc();
		seriesApi = client.getSeries();

		// For our tutorial/demo we will ensure that the Rapture repositories are present
		blobRepoUri = createBlobRepo();
		docRepoUri = createDocumentRepo();

		rawCsvUri = blobRepoUri + "introDataInbound";
		jsonDocumentUri = docRepoUri + "introDataTranslated";

		System.out.println("Logged in and initialized");
	}

	private void runTutorial() {
		String currentStep = TutorialHelper.getCurrentStep();
		if (currentStep.equals("all") || currentStep.equals("upload")) {
			upload();
		}

		if (currentStep.equals("all") || currentStep.equals("blobToDoc")) {
			blobToDoc();
		}

		if (currentStep.equals("all") || currentStep.equals("docToSeries")) {
			docToSeries();
		}

		System.out.println("Done.");
	}

	private String createBlobRepo() {
		String repoUri = RaptureURI.builder(Scheme.BLOB, BLOB_AUTHORITY).build().toString();

		// If the blob repository does not exist, create it. The configuration in the demonstration
		// creates a blob repository on MONGODB.
		if (!blobApi.blobRepoExists(repoUri)) {
			System.out.println("Creating new blob repo at " + repoUri);
			String config = "BLOB {} USING MONGODB { prefix=\"" + BLOB_AUTHORITY + "\" }";
			String metaConfig = "REP {} USING MONGODB { prefix=\"" + BLOB_AUTHORITY + "\" }";
			blobApi.createBlobRepo(repoUri, config, metaConfig);
		}

		return repoUri;
	}

	private String createDocumentRepo() {
		String repoUri = RaptureURI.builder(Scheme.DOCUMENT, DOC_AUTHORITY).build().toString();

		if (!docApi.docRepoExists(repoUri)) {
			System.out.println("Creating new document repo at " + repoUri);
			// NREP is used for a VERSIONED document repository, in this case on MongoDB
			String config = "NREP {} USING MONGODB { prefix=\"" + DOC_AUTHORITY + "\" }";
			docApi.createDocRepo(repoUri, config);
		}

		return repoUri;
	}

	private void upload() {
		String csvFile = TutorialHelper.getCsvFile();
		try {
			System.out.println("Reading CSV from file " + csvFile);
			File fileHandle = new File(csvFile);
			byte[] rawFileData = new byte[(int) fileHandle.length()];

			FileInputStream fileInputStream = new FileInputStream(fileHandle);
			fileInputStream.read(rawFileData);
			fileInputStream.close();

			System.out.println("Uploading CSV");
			// This is the simple API call for taking a stream of bytes and uploading it as a blob
			blobApi.putBlob(rawCsvUri, rawFileData, "text/csv");
			System.out.println("CSV uploaded to " + rawCsvUri);

		} catch (IOException e) {
			e.printStackTrace();
			abort("There was a problem reading the CSV " + csvFile);
		}
	}

	private void blobToDoc() {
		System.out.println("Retrieving raw CSV content from " + rawCsvUri);
		// This is how you can retrieve blob data from Rapture
		BlobContainer blobContainer = blobApi.getBlob(rawCsvUri);
		if (blobContainer == null) {
			abort("Nothing found at " + rawCsvUri + ". Please run step 'upload' to add the CSV to Rapture.");
		}

		byte[] rawCsvData = blobContainer.getContent();

		System.out.println("Translating raw CSV content to a JSON document");
		BufferedReader reader = new BufferedReader(new InputStreamReader(new ByteArrayInputStream(rawCsvData)));

		try {
			String delimiter = ",";
			String csvLine = reader.readLine();
			String[] headers = csvLine.split(delimiter);

			String seriesType = "";
			String frequency = "";

			IndexToPriceTypeMap indexToPriceTypeMap = new IndexToPriceTypeMap();
			while ((csvLine = reader.readLine()) != null) {
				String[] data = csvLine.split(delimiter);
				if (headers.length != data.length) {
					throw new DataFormatException("Invalid CSV format");
				}

				if (seriesType.isEmpty()) {
					// Business rules tell us these will always be the same for
					// every row in the CSV
					seriesType = data[SERIES_TYPE_INDEX];
					frequency = data[FREQUENCY_INDEX];
				}

				// Build a nested map of the rest of the data
				PriceTypeToDateMap currentPriceTypeToDateMap = new PriceTypeToDateMap();
				DateToPriceMap currentDateToPriceMap = new DateToPriceMap();
				for (int i = INDEX_ID_INDEX; i < data.length - 1; i++) {
					switch (i) {
					case INDEX_ID_INDEX:
						if (!indexToPriceTypeMap.containsKey(data[i])) {
							indexToPriceTypeMap.put(data[i], new PriceTypeToDateMap());
						}
						currentPriceTypeToDateMap = indexToPriceTypeMap.get(data[i]);
						break;
					case FREQUENCY_INDEX:
						continue;
					case PRICE_TYPE_INDEX:
						if (!currentPriceTypeToDateMap.containsKey(data[i])) {
							currentPriceTypeToDateMap.put(data[i], new DateToPriceMap());
						}
						currentDateToPriceMap = currentPriceTypeToDateMap.get(data[i]);
						break;
					case DATE_INDEX:
						currentDateToPriceMap.put(data[i], Double.parseDouble(data[i + 1]));
						break;
					}
				}
			}

			Map<String, Object> finalMap = new LinkedHashMap<String, Object>();
			finalMap.put(SERIES_TYPE_HEADER, seriesType);
			finalMap.put(FREQUENCY_HEADER, frequency);
			finalMap.put(INDEX_ID_HEADER, indexToPriceTypeMap);

			// JacksonUtil (using the Jackson JSON/Object parser) is used to convert a map of maps into a JSON formatted
			// text string, which we then put into Rapture.
			String jsonDocument = JacksonUtil.jsonFromObject(finalMap);

			System.out.println("Storing JSON document in Rapture");
			docApi.putDoc(jsonDocumentUri, jsonDocument);
		} catch (IOException e) {
			e.printStackTrace();
			abort("There was a problem reading the CSV.");
		} catch (DataFormatException e) {
			e.printStackTrace();
			abort("There was a problem with the format of the CSV.");
		}
	}

	class DateToPriceMap extends TreeMap<String, Double> {
	}

	class PriceTypeToDateMap extends TreeMap<String, DateToPriceMap> {
	}

	class IndexToPriceTypeMap extends TreeMap<String, PriceTypeToDateMap> {
	}

	private void docToSeries() {
		String seriesRepoUri = RaptureURI.builder(Scheme.SERIES, SERIES_AUTHORITY).build().toString();
		System.out.println("Adding price data from " + jsonDocumentUri + " to series repo " + seriesRepoUri);

		String jsonDocument = docApi.getDoc(jsonDocumentUri);
		if (jsonDocument == null) {
			abort("No data found at " + jsonDocumentUri
					+ ". Please run step 'blobToDoc' to transform the raw CSV into a Rapture document.");
		}

		Map<String, Object> outerMap = JacksonUtil.getMapFromJson(jsonDocument);
		Map<String, Object> innerMap = (Map<String, Object>) outerMap.get(INDEX_ID_HEADER);

		String seriesUriBase = seriesRepoUri + outerMap.get(SERIES_TYPE_HEADER) + "/";
		for (Map.Entry<String, Object> indexMapEntry : innerMap.entrySet()) {
			String seriesUriWithIndex = seriesUriBase + indexMapEntry.getKey() + "/" + outerMap.get(FREQUENCY_HEADER)
					+ "/";

			for (Map.Entry<String, Object> priceTypeMapEntry : ((Map<String, Object>) indexMapEntry.getValue())
					.entrySet()) {
				String seriesUriWithPriceType = seriesUriWithIndex + priceTypeMapEntry.getKey();

				for (Map.Entry<String, Double> dateMapEntry : ((Map<String, Double>) priceTypeMapEntry.getValue())
						.entrySet()) {
					// In this case we are writing the series data one point at a time. The key is (will be) a text formatted
					// date style string, the value will be a double.
					seriesApi.addDoubleToSeries(seriesUriWithPriceType, dateMapEntry.getKey(), dateMapEntry.getValue());
				}
			}
		}
	}

	private void abort(String reason) {
		System.out.println();
		System.out.println(reason);
		System.exit(1);
	}

}
