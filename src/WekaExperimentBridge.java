import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import weka.core.*;
import weka.associations.*;
import weka.clusterers.SimpleKMeans;

/** Bridge to the installed Weka library; datasets contain no customer IDs as features. */
public class WekaExperimentBridge {
    static String csv(String value) { return "\"" + value.replace("\"", "\"\"") + "\""; }
    static PrintWriter writer(Path path) throws IOException {
        return new PrintWriter(Files.newBufferedWriter(path, StandardCharsets.UTF_8));
    }
    static String side(Collection<Item> items) {
        ArrayList<String> names = new ArrayList<>();
        for (Item item : items) {
            if (!item.getItemValueAsString().equals("present")) {
                throw new IllegalStateException("A negative/absent item entered a rule: " + item);
            }
            names.add(item.getAttribute().name());
        }
        Collections.sort(names);
        return String.join("|", names);
    }
    static List<int[]> transactions(Path path) throws IOException {
        ArrayList<int[]> rows = new ArrayList<>();
        for (String line : Files.readAllLines(path, StandardCharsets.UTF_8)) {
            String clean = line.trim();
            if (clean.isEmpty()) { rows.add(new int[0]); continue; }
            rows.add(Arrays.stream(clean.split(" ")).mapToInt(Integer::parseInt).toArray());
        }
        return rows;
    }
    static Instances binaryData(List<String> codes, List<int[]> rows, int minimumCount) {
        int[] counts = new int[codes.size()];
        for (int[] row : rows) for (int item : row) counts[item]++;
        int[] map = new int[codes.size()]; Arrays.fill(map, -1);
        ArrayList<Attribute> attributes = new ArrayList<>();
        for (int i=0; i<codes.size(); i++) if (counts[i] >= minimumCount) {
            map[i] = attributes.size();
            attributes.add(new Attribute(codes.get(i), new ArrayList<>(Arrays.asList("absent", "present"))));
        }
        if (attributes.isEmpty()) throw new IllegalArgumentException("No item meets minimum support.");
        Instances data = new Instances("invoice_binary_positive_items", attributes, rows.size());
        for (int[] row : rows) {
            double[] values = new double[attributes.size()];
            for (int item : row) if (map[item]>=0) values[map[item]]=1.0;
            data.add(new DenseInstance(1.0, values));
        }
        data.setClassIndex(-1);
        return data;
    }
    static AssociationRules mine(String algorithm, Instances data, double effectiveSupport, int maxItems) throws Exception {
        if (algorithm.equals("apriori")) {
            Apriori model = new Apriori();
            model.setTreatZeroAsMissing(true);
            model.setRemoveAllMissingCols(false);
            model.setUpperBoundMinSupport(1.0);
            model.setLowerBoundMinSupport(effectiveSupport);
            model.setDelta(1.0);
            model.setMinMetric(0.0);
            model.setNumRules(1000000);
            model.buildAssociations(data);
            AssociationRules rules = model.getAssociationRules();
            if (rules.getRules().size()>=1000000) throw new IllegalStateException("Apriori rule cap reached.");
            return rules;
        }
        FPGrowth model = new FPGrowth();
        model.setPositiveIndex(2);
        model.setUpperBoundMinSupport(1.0);
        model.setLowerBoundMinSupport(effectiveSupport);
        model.setFindAllRulesForSupportLevel(true);
        model.setNumRulesToFind(1000000);
        model.setMinMetric(0.0);
        model.setMaxNumberOfItems(maxItems);
        model.buildAssociations(data);
        return model.getAssociationRules();
    }
    static int writeRules(AssociationRules rules, Path output, int n, int minimumCount, int reportMaxItems) throws Exception {
        int written = 0;
        try (PrintWriter out=writer(output)) {
            out.println("antecedent,consequent,count_a,count_b,count_ab,n_transactions");
            for (AssociationRule rule : rules.getRules()) {
                if (rule.getTotalTransactions()!=n) throw new IllegalStateException("Transaction denominator changed.");
                if (rule.getTotalSupport()<minimumCount) continue;
                if (rule.getPremise().size()+rule.getConsequence().size()>reportMaxItems) continue;
                out.println(csv(side(rule.getPremise()))+","+csv(side(rule.getConsequence()))+","+rule.getPremiseSupport()+","+rule.getConsequenceSupport()+","+rule.getTotalSupport()+","+rule.getTotalTransactions());
                written++;
            }
        }
        return written;
    }
    static void ruleExperiments(String[] args) throws Exception {
        List<String> codes=Files.readAllLines(Paths.get(args[1]),StandardCharsets.UTF_8);
        List<int[]> rows=transactions(Paths.get(args[2]));
        Path output=Paths.get(args[3]); Files.createDirectories(output);
        double[] supports=Arrays.stream(args[4].split(",")).mapToDouble(Double::parseDouble).toArray();
        int repeats=Integer.parseInt(args[5]);
        String mode=args.length>6?args[6]:"both";
        boolean boundedOnly=mode.equals("fpgrowth_bounded_only");
        int minCount=Math.max(1,(int)Math.ceil(Arrays.stream(supports).min().getAsDouble()*rows.size()-1e-10));
        Instances data=binaryData(codes, rows, minCount);
        try (PrintWriter timings=writer(output.resolve("benchmark.csv"))) {
            timings.println("algorithm,requested_support,minimum_count,effective_weka_support,repeat,fit_and_rule_generation_ms,all_generated_rules,reported_max3_rules,n_transactions,frequent_singleton_columns,mining_max_items");
            for (int s=0; s<supports.length; s++) {
                int required=Math.max(1,(int)Math.ceil(supports[s]*rows.size()-1e-10));
                // Weka Apriori rounds whereas FP-Growth ceils support*N. This yields the same integer threshold.
                double effective=(required-0.25)/rows.size();
                for (int repeat=0; repeat<repeats; repeat++) {
                    String[] order=mode.startsWith("fpgrowth") ? new String[]{"fpgrowth"} : mode.equals("apriori_only") ? new String[]{"apriori"} : repeat%2==0 ? new String[]{"apriori","fpgrowth"} : new String[]{"fpgrowth","apriori"};
                    for (String algorithm : order) {
                        long start=System.nanoTime();
                        AssociationRules rules=mine(algorithm, new Instances(data), effective, boundedOnly?3:-1);
                        double millis=(System.nanoTime()-start)/1e6;
                        int written=writeRules(rules, output.resolve(algorithm+"_s"+s+"_rules.csv"),rows.size(),required,3);
                        timings.printf(Locale.US,"%s,%.12f,%d,%.12f,%d,%.6f,%d,%d,%d,%d,%d%n",algorithm,supports[s],required,effective,repeat,millis,rules.getRules().size(),written,rows.size(),data.numAttributes(),boundedOnly?3:-1);
                        timings.flush();
                        System.out.printf(Locale.US,"%s support %.4f rep %d: %d reported rules in %.1f ms%n",algorithm,supports[s],repeat,written,millis);
                    }
                }
            }
        }
    }
    static Instances features(Path path) throws IOException {
        List<String> lines=Files.readAllLines(path,StandardCharsets.UTF_8);
        ArrayList<Attribute> attributes=new ArrayList<>();
        attributes.add(new Attribute("RecencyLogZ")); attributes.add(new Attribute("FrequencyLogZ")); attributes.add(new Attribute("MonetaryLogZ"));
        Instances data=new Instances("rfm_train_standardized",attributes,lines.size()-1);
        for (int i=1;i<lines.size();i++) {
            String[] fields=lines.get(i).split(",");
            if (fields.length!=4) throw new IllegalArgumentException("Expected CustomerID and exactly three features.");
            data.add(new DenseInstance(1.0,new double[]{Double.parseDouble(fields[1]),Double.parseDouble(fields[2]),Double.parseDouble(fields[3])}));
        }
        return data;
    }
    static void clusters(String[] args) throws Exception {
        Instances data=features(Paths.get(args[1])); Path output=Paths.get(args[2]); Files.createDirectories(output);
        int nInit=Integer.parseInt(args[3]);
        try (PrintWriter fits=writer(output.resolve("weka_kmeans_fits.csv")); PrintWriter centers=writer(output.resolve("weka_kmeans_centers.csv"))) {
            fits.println("k,base_seed,n_init,best_actual_seed,sse,fit_ms,n_customers");
            centers.println("k,base_seed,raw_cluster,RecencyLogZ,FrequencyLogZ,MonetaryLogZ");
            for (int k=2;k<=8;k++) for (int base=42;base<=46;base++) {
                SimpleKMeans best=null; double bestSSE=Double.POSITIVE_INFINITY; int actualSeed=-1;
                long start=System.nanoTime();
                for (int init=0;init<nInit;init++) {
                    SimpleKMeans model=new SimpleKMeans();
                    model.setNumClusters(k); model.setSeed(base+1009*init); model.setMaxIterations(300);
                    model.setInitializationMethod(new SelectedTag(SimpleKMeans.KMEANS_PLUS_PLUS,SimpleKMeans.TAGS_SELECTION));
                    model.setPreserveInstancesOrder(true); model.setFastDistanceCalc(false); model.setNumExecutionSlots(1);
                    EuclideanDistance distance=new EuclideanDistance(); distance.setDontNormalize(true); model.setDistanceFunction(distance);
                    model.buildClusterer(data);
                    if (model.numberOfClusters()!=k) throw new IllegalStateException("Fewer clusters than requested.");
                    if (model.getSquaredError()<bestSSE) { best=model;bestSSE=model.getSquaredError();actualSeed=base+1009*init; }
                }
                double milliseconds=(System.nanoTime()-start)/1e6;
                int[] labels=best.getAssignments();
                try(PrintWriter out=writer(output.resolve("k"+k+"_seed"+base+"_labels.csv"))) {
                    out.println("row_index,raw_cluster"); for(int i=0;i<labels.length;i++) out.println(i+","+labels[i]);
                }
                Instances centroids=best.getClusterCentroids();
                for(int c=0;c<centroids.numInstances();c++) centers.printf(Locale.US,"%d,%d,%d,%.15g,%.15g,%.15g%n",k,base,c,centroids.instance(c).value(0),centroids.instance(c).value(1),centroids.instance(c).value(2));
                fits.printf(Locale.US,"%d,%d,%d,%d,%.12f,%.6f,%d%n",k,base,nInit,actualSeed,bestSSE,milliseconds,data.numInstances());fits.flush();centers.flush();
                if(base==42) SerializationHelper.write(output.resolve("k"+k+"_seed42.model").toString(),best);
                System.out.printf(Locale.US,"k=%d base=%d SSE=%.5f%n",k,base,bestSSE);
            }
        }
    }
    public static void main(String[] args) throws Exception {
        Locale.setDefault(Locale.US);
        if(args[0].equals("rules")) ruleExperiments(args);
        else if(args[0].equals("clusters")) clusters(args);
        else throw new IllegalArgumentException("Unknown experiment mode.");
    }
}
