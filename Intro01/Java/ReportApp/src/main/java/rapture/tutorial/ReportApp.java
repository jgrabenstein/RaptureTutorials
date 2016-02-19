package rapture.tutorial;

import java.awt.Graphics2D;
import java.awt.geom.Rectangle2D;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.List;
import java.util.Map;
import java.util.Scanner;

import org.apache.commons.lang3.StringUtils;
import org.apache.log4j.Logger;
import org.jfree.chart.ChartFactory;
import org.jfree.chart.JFreeChart;
import org.jfree.chart.axis.CategoryLabelPositions;
import org.jfree.chart.plot.PlotOrientation;
import org.jfree.data.category.DefaultCategoryDataset;

import com.google.common.collect.ImmutableMap;
import com.lowagie.text.Document;
import com.lowagie.text.DocumentException;
import com.lowagie.text.pdf.DefaultFontMapper;
import com.lowagie.text.pdf.PdfContentByte;
import com.lowagie.text.pdf.PdfTemplate;
import com.lowagie.text.pdf.PdfWriter;

import rapture.common.RaptureFolderInfo;
import rapture.common.SeriesPoint;
import rapture.common.client.HttpBlobApi;
import rapture.common.client.HttpLoginApi;
import rapture.common.client.HttpSeriesApi;
import rapture.common.client.SimpleCredentialsProvider;

/**
 * Sample application used to read a series in Rapture, and then generate a line graph for it and output it to a PDF file. Charting and PDF generation uses
 * third-party libraries JFreeChart and iText.
 * 
 * @author dukenguyen
 */
public class ReportApp {

    private static final Logger log = Logger.getLogger(ReportApp.class);
    private static final String FILENAME = "output.pdf";
    private static final String FIELD = "PX_LAST";
    private static final String TITLE_CHART = "Last Price Data";
    private static final int NUM_POINTS = 50;
    private static final Map<String, String> INDEX_IDS = ImmutableMap.<String, String> of(
            "AUDUSD_CURNCY_Dummy", "AUD USD Currency",
            "USGG2YR_Index_Dummy", "USGG2YR Index");

    private String host;
    private SimpleCredentialsProvider credentials;

    public static void main(String[] args) {
        ReportApp dr = new ReportApp();
        dr.run(args);
    }

    private void run(String[] args) {
        readLoginInfo(args);
        log.info("Starting ReportApp...");
        //ask whether they are working with java, rfx, or py series
        Scanner scanner = new Scanner(System.in);
        System.out.print("Are we analyzing series from Java, Reflex or Python?: ");
        String language = scanner.next().substring(0,1).toUpperCase()+scanner.next().substring(1);
        HttpLoginApi login = new HttpLoginApi(host, credentials);
        login.login();
        HttpSeriesApi series = new HttpSeriesApi(login);
        DefaultCategoryDataset dataSet = new DefaultCategoryDataset();
        for (Map.Entry<String, String> entry : INDEX_IDS.entrySet()) {
            log.info("Processing: " + entry.getKey());
            // make the api call to the rapture series api to get the points
            List<SeriesPoint> points = series.getPoints(String.format("series://datacapture/HIST/TutorialIntro_"+language+"/%s/DAILY/%s", entry.getKey(), FIELD));
            // only graph the last NUM_POINTS points
            points = points.subList(points.size() - NUM_POINTS, points.size());
            for (SeriesPoint point : points) {
                dataSet.addValue(Double.parseDouble(point.getValue()), entry.getValue(), point.getColumn());
            }
        }
        scanner.close();
        // create a graph given the data set of points that we have
        JFreeChart chart = ChartFactory.createLineChart(TITLE_CHART, "Date", "Price", dataSet, PlotOrientation.VERTICAL, true, true, false);
        chart.getCategoryPlot().getDomainAxis().setCategoryLabelPositions(CategoryLabelPositions.UP_90);
        writeChartToPDF(chart, 600, 480, FILENAME);
        log.info("Successfully generated report: " + FILENAME);
        try {
            byte[] pdfBytes = Files.readAllBytes(Paths.get(FILENAME));
            HttpBlobApi blob = new HttpBlobApi(login);
            // make the rapture api call to store the generated pdf back into rapture
            blob.putBlob(String.format("blob://tutorialBlob/%s", FILENAME), pdfBytes, "application/pdf");
            log.info("Successfully uploaded report: " + FILENAME);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    /**
     * Method to get parameters from the command-line
     * 
     * @param args
     */
    private void readLoginInfo(String[] args) {
        if (args.length == 2) {
            host = args[0];
            credentials = new SimpleCredentialsProvider(args[1], new String(System.console().readPassword("Password: ")));
        } else {
            String hostFromEnv = System.getenv("RAPTURE_HOST");
            String userFromEnv = System.getenv("RAPTURE_USER");
            if (!StringUtils.isBlank(hostFromEnv) && !StringUtils.isBlank(userFromEnv)) {
                host = hostFromEnv;
                credentials = new SimpleCredentialsProvider(userFromEnv, new String(System.console().readPassword("Password: ")));
            } else {
                log.error("Usage: ./ReportApp <host> <user>");
                System.exit(1);
            }
        }
    }

    /**
     * Write a JFreeChart object out to a pdf file
     * 
     * @param chart
     * @param width
     * @param height
     * @param fileName
     */
    private void writeChartToPDF(JFreeChart chart, int width, int height, String fileName) {
        PdfWriter writer = null;
        Document document = new Document();
        try {
            writer = PdfWriter.getInstance(document, new FileOutputStream(fileName));
            document.open();
            PdfContentByte contentByte = writer.getDirectContent();
            PdfTemplate template = contentByte.createTemplate(width, height);
            Graphics2D graphics2d = template.createGraphics(width, height, new DefaultFontMapper());
            Rectangle2D rectangle2d = new Rectangle2D.Double(0, 0, width, height);
            chart.draw(graphics2d, rectangle2d);
            graphics2d.dispose();
            contentByte.addTemplate(template, 0, 0);
        } catch (DocumentException | FileNotFoundException e) {
            e.printStackTrace();
        } finally {
            document.close();
            if (writer != null) {
                writer.close();
            }
        }
    }
}
