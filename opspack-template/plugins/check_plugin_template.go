package main

import (
	"github.com/opsview/go-plugin"
)

var opts struct {
	Hostname string `short:"H" long:"hostname" description:"IP address for Host"`
	Port     string `short:"P" long:"port" description:"Port for Host"`
	Mode     string `short:"m" long:"mode" description:"Mode/Metric to monitor"`
	Warning  string `short:"w" long:"warning" description:"Warning"`
	Critical string `short:"c" long:"critical" description:"Critical"`
}

func main() {
	// Main function creates the new plugin instance, then calls function to retrieve metrics
	// For the required metric it retrieves the stat and adds it to the output
	// Switches into various cases depending on which metric is needed

	check := plugin.New("check_example", "v1.0.0") 
	if err := check.ParseArgs(&opts); err != nil {
		// Handles error if incorrect arguments entered
		check.ExitUnknown("Error parsing arguments: %s", err)
	}

	defer check.Final() // Calculates the final output after function completes

	check.AllMetricsInOutput = true // So that all metrics are added to the summary message

	check.AddMetric(opts.Mode, 10, "%", opts.Warning, opts.Critical)
}
