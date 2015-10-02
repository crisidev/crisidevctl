package main

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path"
	"strings"
	"sync"
	"time"

	"github.com/coreos/etcd/Godeps/_workspace/src/golang.org/x/net/context"
	"github.com/coreos/etcd/client"
	"gopkg.in/alecthomas/kingpin.v2"
)

const (
	WORKDIR = "/crisidev-share"
)

var (
	flagWatchDir     = kingpin.Flag("watchdir", "directory to watch").Short('w').Default("/crisidev/opus").String()
	flagWorkDir      = kingpin.Flag("workdir", "directory were git repos are stored").Short('d').Default("/opus").String()
	flagEtcdEndpoint = kingpin.Flag("etcd", "etcd endpoint").Short('e').Default("http://etcd.crisidev.org:4001").String()
)

func init() {
	kingpin.Parse()
}

type Opus struct {
	Build   bool   `json:"build"`
	Dst     string `json:"dst"`
	Restart bool   `json:"restart"`
	Src     string `json:"src"`
}

func GetEtcdClient() (cli client.Client) {
	cfg := client.Config{
		Endpoints: []string{*flagEtcdEndpoint},
		Transport: client.DefaultTransport,
		// set timeout per request to fail fast when the target endpoint is unavailable
		HeaderTimeoutPerRequest: time.Second,
	}
	cli, err := client.New(cfg)
	if err != nil {
		log.Fatal(err)
	}
	return
}

func ExecCommand(command, arguments string) (err error) {
	args := strings.Fields(arguments)
	cmd := exec.Command(command, args...)
	log.Printf("running %s", strings.Join(cmd.Args, " "))
	output, err := cmd.CombinedOutput()
	if err != nil {
		return
	}
	log.Printf(string(output))
	return
}

func Build(source, destination string) (err error) {
	tokens := strings.Split(source, ":")
	gitrepo := tokens[0]
	sourcedir := tokens[1]
	log.Printf("building %s, destination %s", source, destination)
	err = os.Chdir(path.Join(WORKDIR, gitrepo, sourcedir))
	if err != nil {
		return
	}
	err = ExecCommand("git", "pull")
	if err != nil {
		return
	}
	err = ExecCommand("docker", fmt.Sprintf("build -t %s .", destination))
	if err != nil {
		return
	}
	err = ExecCommand("docker", fmt.Sprintf("push %s", destination))
	return
}

func Restart(target string) (err error) {
	log.Printf("stopping container %s", target)
	err = ExecCommand("fleetctl", fmt.Sprintf("-C %s stop %s", *flagEtcdEndpoint, target))
	if err != nil {
		return
	}
	log.Printf("starting container %s", target)
	err = ExecCommand("fleetctl", fmt.Sprintf("-C %s stop %s", *flagEtcdEndpoint, target))
	if err != nil {
		return
	}
	return
}

func Worker(resp *client.Response, wg *sync.WaitGroup) {
	defer wg.Done()
	var opus Opus
	log.Printf("got update under %s. working on container %s", *flagWatchDir, resp.Node.Key)
	json.Unmarshal([]byte(resp.Node.Value), &opus)
	if opus.Build {
		err := Build(opus.Src, opus.Dst)
		if err != nil {
			log.Printf("error building %s: %s", resp.Node.Key, err)
		}
	}

	if opus.Restart {
		err := Restart(resp.Node.Key)
		if err != nil {
			log.Printf("error restarting %s: %s", resp.Node.Key, err)
		}
	}
}

func main() {
	kapi := client.NewKeysAPI(GetEtcdClient())
	log.Printf("watching etcd directory %s", *flagWatchDir)
	watcherOpts := client.WatcherOptions{AfterIndex: 0, Recursive: true}
	w := kapi.Watcher(*flagWatchDir, &watcherOpts)
	for {
		var wg sync.WaitGroup
		resp, err := w.Next(context.Background())
		if err != nil {
			log.Fatal("error occurred", err)
		}
		wg.Add(1)
		go Worker(resp, &wg)
		// do something with Response r here
	}
}
