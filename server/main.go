package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
	"path/filepath"
)

type Entry struct {
	Name  string `json:"name"`
	IsDir bool   `json:"is_dir"`
	Size  int64  `json:"size"`
}

var root string

func safePath(rel string) (string, error) {
	p := filepath.Clean("/" + rel)
	full := filepath.Join(root, p)
	if !filepath.HasPrefix(full, root) {
		return "", os.ErrPermission
	}
	return full, nil
}

func listHandler(w http.ResponseWriter, r *http.Request) {
	rel := r.URL.Query().Get("path")
	full, err := safePath(rel)
	if err != nil {
		http.Error(w, "invalid path", http.StatusBadRequest)
		return
	}

	entries, err := os.ReadDir(full)
	if err != nil {
		http.Error(w, err.Error(), http.StatusNotFound)
		return
	}

	out := make([]Entry, 0, len(entries))
	for _, e := range entries {
		info, _ := e.Info()
		out = append(out, Entry{
			Name:  e.Name(),
			IsDir: e.IsDir(),
			Size:  info.Size(),
		})
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(out)
}

func main() {
	home, err := os.UserHomeDir()
	if err != nil {
		log.Fatal(err)
	}
	root = home

	http.HandleFunc("/api/list", listHandler)
	http.Handle("/file/",
		http.StripPrefix("/file/",
			http.FileServer(http.Dir(root)),
		),
	)

	log.Println("listening on 127.0.0.1:9000")
	log.Fatal(http.ListenAndServe("127.0.0.1:9000", nil))
}

