package rapture.tutorial;

import java.io.Console;
import java.io.PrintWriter;
import java.util.Arrays;

import org.apache.commons.cli.CommandLine;
import org.apache.commons.cli.CommandLineParser;
import org.apache.commons.cli.GnuParser;
import org.apache.commons.cli.HelpFormatter;
import org.apache.commons.cli.Options;
import org.apache.commons.cli.ParseException;

/**
 * A simple static utility class to read options for the tutorial.
 * 
 * Depending on how the demonstration environment is setup the environment
 * variables for Rapture may have already been setup. If not you will have to
 * provide them on the command line.
 * 
 * @author amkimian
 *
 */
public class TutorialHelper {
	private static String host;
	private static String username;
	private static char[] password;
	private static String currentStep;
	private static String[] steps = { "upload", "blobToDoc", "docToSeries", "all" };
	private static String csvFile;

	public static Options getOptions() {

		String stepList = "";
		for (String step : steps) {
			stepList += " " + step;
		}

		Options options = new Options();
		options.addOption("h", "host", true, "Rapture host").addOption("u", "user", true, "Rapture username")
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

			if (commandLine.hasOption("h")) {
				host = commandLine.getOptionValue("h");
			} else {
				host = System.getenv("RAPTURE_HOST");
			}
			if (host == null) {
				System.out.println(
						"No Rapture host specified. Please set the environment variable RAPTURE_HOST or supply the -h option on the command line.");
				missingOptions = true;
			}

			if (commandLine.hasOption("u")) {
				username = commandLine.getOptionValue("u");
			} else {
				username = System.getenv("RAPTURE_USER");
			}
			if (username == null) {
				System.out.println(
						"No Rapture user specified. Please set the environment variable RAPTURE_USER or supply the -u option on the command line.");
				missingOptions = true;
			}

			if (commandLine.hasOption("p")) {
				password = ((String) commandLine.getOptionValue("p")).toCharArray();
			} else {
				String envPasswd = System.getenv("RAPTURE_PASSWORD");
				if (envPasswd != null) {
					password = envPasswd.toCharArray();
				}
			}
			if (password == null) {
				Console cons;
				if ((cons = System.console()) == null || (password = cons.readPassword("%s", "Password:")) == null) {
					System.out.println(
							"No Rapture password specified. Please set the environment variable RAPTURE_PASSWORD or supply the -p option on the command line.");
					missingOptions = true;
				}
			}

			if (commandLine.hasOption("s")) {
				currentStep = commandLine.getOptionValue("s");
			}
			if (!Arrays.asList(steps).contains(currentStep)) {
				System.out.println("No tutorial step specified. Please supply the -s option on the command line.");
				missingOptions = true;
			}

			if (commandLine.hasOption("f")) {
				csvFile = commandLine.getOptionValue("f");
			} else {
				csvFile = System.getenv("RAPTURE_TUTORIAL_CSV");
			}
			if (csvFile == null && currentStep.equals("upload")) {
				System.out.println(
						"No CSV specified. Please set the environment variable RAPTURE_TUTORIAL_CSV or supply the -f option on the command line.");
				missingOptions = true;
			}

			if (missingOptions || commandLine.hasOption("?")) {
				displayHelp();
			}
		} catch (ParseException parseException) {
			System.err.println(
					"Encountered exception while parsing command line options:\n" + parseException.getMessage());
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

		helpFormatter.printHelp(writer, printedRowWidth, commandLineSyntax, header, options, spacesBeforeOption,
				spacesBeforeOptionDescription, footer, displayUsage);
		writer.close();

		System.exit(0);
	}

	public static String getHost() {
		return host;
	}

	public static String getUserName() {
		return username;
	}

	public static char[] getPassword() {
		return password;
	}

	public static String getCurrentStep() {
		return currentStep;
	}

	public static String getCsvFile() {
		return csvFile;
	}
}
