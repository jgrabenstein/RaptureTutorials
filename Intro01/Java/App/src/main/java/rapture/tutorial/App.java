package rapture.tutorial;

import org.apache.commons.cli.CommandLine;
import org.apache.commons.cli.CommandLineParser;
import org.apache.commons.cli.GnuParser;
import org.apache.commons.cli.HelpFormatter;
import org.apache.commons.cli.Options;
import org.apache.commons.cli.ParseException;
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

import java.io.BufferedReader;
import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.PrintWriter;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.TreeMap;
import java.util.zip.DataFormatException;

public class App {
    private static ScriptClient client;
    private HttpLoginApi loginApi;
    private HttpBlobApi blobApi;
    private HttpDocApi docApi;
    private HttpSeriesApi seriesApi;

    private static String host;
    private static String username;
    private static String password;
    private static String csvFile;
    private static String currentStep = "";

    private static String[] steps = {"upload", "blobToDoc", "docToSeries", "all"};

    private static final String SERIES_AUTHORITY = "datacapture";
    private static final String BLOB_AUTHORITY = "tutorialBlob";
    private static final String DOC_AUTHORITY = "tutorialDoc";

    private String blobRepoUri;
    private String docRepoUri;
    private String rawCsvUri;
    private String jsonDocumentUri;

    private static final String SERIES_TYPE_HEADER = "series_type";
    private static final String PROVIDER_HEADER = "provider";
    private static final String FREQUENCY_HEADER = "frequency";
    private static final String INDEX_ID_HEADER = "index_id";
    private static final int SERIES_TYPE_INDEX = 0;
    private static final int PROVIDER_INDEX = 1;
    private static final int INDEX_ID_INDEX = 2;
    private static final int FREQUENCY_INDEX = 3;

    public static final void main(String args[]) {
        App tutorialApp = new App();

        parseOptions(args);
        tutorialApp.init();

        tutorialApp.runTutorial();
    }

    private void init() {
        System.out.println("Starting up..");
        System.out.println("Logging in to " + host);

        SimpleCredentialsProvider creds = new SimpleCredentialsProvider(username, password);
        loginApi = new HttpLoginApi(host, creds);
        loginApi.login();

        client = new ScriptClient(loginApi);

        blobApi = client.getBlob();
        docApi = client.getDoc();
        seriesApi = client.getSeries();

        blobRepoUri = createBlobRepo();
        docRepoUri = createDocumentRepo();

        rawCsvUri = blobRepoUri + "introDataInbound.csv";
        jsonDocumentUri = docRepoUri + "introDataTranslated";

        System.out.println("Logged in and initialized");
    }

    private void runTutorial() {
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

        if(!blobApi.blobRepoExists(repoUri)) {
            System.out.println("Creating new blob repo at " + repoUri);
            String config = "BLOB {} USING MONGODB { prefix=\"" + BLOB_AUTHORITY + "\" }";
            String metaConfig = "REP {} USING MEMORY { prefix=\"" + BLOB_AUTHORITY + "\" }";
            blobApi.createBlobRepo(repoUri, config, metaConfig);
        }

        return repoUri;
    }


    private String createDocumentRepo() {
        String repoUri = RaptureURI.builder(Scheme.DOCUMENT, DOC_AUTHORITY).build().toString();

        if(!docApi.docRepoExists(repoUri)) {
            System.out.println("Creating new document repo at " + repoUri);
            String config = "NREP {} USING MONGODB { prefix=\"" + DOC_AUTHORITY + "\" }";
            docApi.createDocRepo(repoUri, config);
        }

        return repoUri;
    }

    private void upload() {
        try {
            System.out.println("Reading CSV from file " + csvFile);
            File fileHandle = new File(csvFile);
            byte[] rawFileData = new byte[(int) fileHandle.length()];

            FileInputStream fileInputStream = new FileInputStream(fileHandle);
            fileInputStream.read(rawFileData);
            fileInputStream.close();

            System.out.println("Uploading CSV");
            blobApi.putBlob(rawCsvUri, rawFileData, "text/csv");
            System.out.println("CSV uploaded to " + rawCsvUri);

        } catch(IOException e) {
            e.printStackTrace();
            abort("There was a problem reading the CSV " + csvFile);
        }
    }

    private void blobToDoc() {
        System.out.println("Retrieving raw CSV content from " + rawCsvUri);
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

            String provider = "";
            String seriesType = "";
            String frequency = "";

            Map<String, Object> nestedMap = new TreeMap();
            while ((csvLine = reader.readLine()) != null) {
                String[] data = csvLine.split(delimiter);
                if (headers.length != data.length) {
                    throw new DataFormatException("Invalid CSV format");
                }

                if (provider.isEmpty()) {
                    // Business rules tell us these will always be the same for every row in the CSV
                    provider = data[PROVIDER_INDEX];
                    seriesType = data[SERIES_TYPE_INDEX];
                    frequency = data[FREQUENCY_INDEX];
                }

                // Build a nested map of the rest of the data
                Map<String, Object> currentMapLevel = nestedMap;
                for (int i = INDEX_ID_INDEX; i < data.length - 1; i++) {
                    if (i == FREQUENCY_INDEX) {
                        continue;
                    }

                    if (i == data.length - 2) {
                        // If we've reached the last two values, add them as a simple key-value pair
                        currentMapLevel.put(data[i], Double.parseDouble(data[i + 1]));
                    }
                    else {
                        // Otherwise, make sure this key exists in the current map level
                        if (!currentMapLevel.containsKey(data[i])) {
                            currentMapLevel.put(data[i], new TreeMap<String, Object>());
                        }

                        // And keep moving down into the nested map
                        currentMapLevel = (Map<String, Object>) currentMapLevel.get(data[i]);
                    }
                }
            }

            Map<String, Object> finalMap = new LinkedHashMap();
            finalMap.put(PROVIDER_HEADER, provider);
            finalMap.put(SERIES_TYPE_HEADER, seriesType);
            finalMap.put(FREQUENCY_HEADER, frequency);
            finalMap.put(INDEX_ID_HEADER, nestedMap);

            String jsonDocument = JacksonUtil.jsonFromObject(finalMap);

            System.out.println("Storing JSON document in Rapture");
            docApi.putDoc(jsonDocumentUri, jsonDocument);
        }
        catch (IOException e) {
            e.printStackTrace();
            abort("There was a problem reading the CSV.");
        }
        catch (DataFormatException e) {
            e.printStackTrace();
            abort("There was a problem with the format of the CSV.");
        }
    }



    private void docToSeries() {
        String seriesRepoUri = RaptureURI.builder(Scheme.SERIES, SERIES_AUTHORITY).build().toString();
        System.out.println("Adding price data from " + jsonDocumentUri + " to series at " + seriesRepoUri);

        String jsonDocument = docApi.getDoc(jsonDocumentUri);
        if (jsonDocument == null) {
            abort("No data found at " + jsonDocumentUri + ". Please run step 'blobToDoc' to transform the raw CSV into a Rapture document.");
        }

        Map<String, Object> outerMap = JacksonUtil.getMapFromJson(jsonDocument);
        Map<String, Object> innerMap = (Map<String, Object>) outerMap.get(INDEX_ID_HEADER);

        String seriesUriBase = seriesRepoUri + outerMap.get(SERIES_TYPE_HEADER) + "/" + outerMap.get(PROVIDER_HEADER) + "/";
        for (Map.Entry<String, Object> indexMapEntry: innerMap.entrySet()) {
            String seriesUriWithIndex = seriesUriBase + indexMapEntry.getKey() + "/" + outerMap.get(FREQUENCY_HEADER) + "/";

            for (Map.Entry<String, Object> priceTypeMapEntry: ((Map<String, Object>) indexMapEntry.getValue()).entrySet()) {
                String seriesUriWithPriceType = seriesUriWithIndex + priceTypeMapEntry.getKey();

                for (Map.Entry<String, Double> dateMapEntry: ((Map<String, Double>) priceTypeMapEntry.getValue()).entrySet()) {
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

    public static Options getOptions() {
        String stepList = "";
        for (String step: steps) {
            stepList += " " + step;
        }

        Options options = new Options();
        options.addOption("h", "host", true, "Rapture host")
                .addOption("u", "user", true, "Rapture username")
                .addOption("p", "password", true, "Rapture password")
                .addOption("f", "file", true, "Fully qualified path to CSV file")
                .addOption("s", "step", true, "Step to execute: " + stepList)
                .addOption("?", "help", false, "Display this help message");
        return options;
    }

    public static void parseOptions(String[] commandLineArguments) {
        CommandLineParser parser = new GnuParser();

        Options gnuOptions = getOptions();
        CommandLine commandLine;
        try {
            commandLine = parser.parse(gnuOptions, commandLineArguments);
            boolean missingOptions = false;

            if ( commandLine.hasOption("h") ) {
                host = commandLine.getOptionValue("h");
            }
            else {
                host = System.getenv("RAPTURE_HOST");
            }
            if (host == null) {
                System.out.println("No Rapture host specified. Please set the environment variable RAPTURE_HOST or supply the -h option on the command line.");
                missingOptions = true;
            }

            if ( commandLine.hasOption("u") ) {
                username = commandLine.getOptionValue("u");
            }
            else {
                username = System.getenv("RAPTURE_USER");
            }
            if (username == null) {
                System.out.println("No Rapture user specified. Please set the environment variable RAPTURE_USER or supply the -u option on the command line.");
                missingOptions = true;
            }

            // TODO: better password handling
            if ( commandLine.hasOption("p") ) {
                password = commandLine.getOptionValue("p");
            }
            else {
                password = System.getenv("RAPTURE_PASSWORD");
            }
            if (password == null) {
                System.out.println("No Rapture password specified. Please set the environment variable RAPTURE_PASSWORD or supply the -p option on the command line.");
                missingOptions = true;
            }

            if ( commandLine.hasOption("f") ) {
                csvFile = commandLine.getOptionValue("f");
            }
            else {
                csvFile = System.getenv("RAPTURE_TUTORIAL_CSV");
            }
            if (csvFile == null) {
                System.out.println("No CSV specified. Please set the environment variable RAPTURE_TUTORIAL_CSV or supply the -f option on the command line.");
                missingOptions = true;
            }

            if ( commandLine.hasOption("s") ) {
                currentStep = commandLine.getOptionValue("s");
            }
            if (!Arrays.asList(steps).contains(currentStep)) {
                System.out.println("No tutorial step specified. Please supply the -s option on the command line.");
                missingOptions = true;
            }

            if (missingOptions || commandLine.hasOption("?")) {
                displayHelp();
            }
        }
        catch (ParseException parseException) {
            System.err.println("Encountered exception while parsing command line options:\n" + parseException.getMessage());
        }
    }

    public static void displayHelp() {
        PrintWriter writer = new PrintWriter(System.out);
        HelpFormatter helpFormatter = new HelpFormatter();

        int printedRowWidth = 80;
        String commandLineSyntax = "App";
        String header = "Options:";
        Options options = getOptions();
        int spacesBeforeOption = 2;
        int spacesBeforeOptionDescription = 2;
        String footer = "";
        boolean displayUsage = true;

        helpFormatter.printHelp(
                writer,
                printedRowWidth,
                commandLineSyntax,
                header,
                options,
                spacesBeforeOption,
                spacesBeforeOptionDescription,
                footer,
                displayUsage);
        writer.close();

        System.exit(0);
    }
}

