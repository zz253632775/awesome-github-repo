package meta

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"time"

	bolt "go.etcd.io/bbolt"
)

var (
	bucketFiles  = []byte("files")
	bucketEvents = []byte("events")
)

type Tier string

const (
	TierTmpfs Tier = "tmpfs"
	TierSSD   Tier = "ssd"
)

type FileRecord struct {
	Path      string    `json:"path"`
	Tier      Tier      `json:"tier"`
	CacheFile string    `json:"cache_file"`
	Size      int64     `json:"size"`
	MTimeUnix int64     `json:"mtime_unix"`
	UpdatedAt time.Time `json:"updated_at"`
	EventID   string    `json:"event_id"`
	State     string    `json:"state"`
}

type Store struct{ db *bolt.DB }

func Open(path string) (*Store, error) {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return nil, fmt.Errorf("create db dir: %w", err)
	}
	db, err := bolt.Open(path, 0o600, &bolt.Options{Timeout: 2 * time.Second})
	if err != nil {
		return nil, err
	}
	if err := db.Update(func(tx *bolt.Tx) error {
		if _, err := tx.CreateBucketIfNotExists(bucketFiles); err != nil {
			return err
		}
		_, err := tx.CreateBucketIfNotExists(bucketEvents)
		return err
	}); err != nil {
		_ = db.Close()
		return nil, err
	}
	return &Store{db: db}, nil
}

func (s *Store) Close() error { return s.db.Close() }

func key(path string, tier Tier) []byte { return []byte(path + "|" + string(tier)) }

func (s *Store) UpsertFile(rec FileRecord) error {
	return s.db.Update(func(tx *bolt.Tx) error {
		b := tx.Bucket(bucketFiles)
		v, err := json.Marshal(rec)
		if err != nil {
			return err
		}
		return b.Put(key(rec.Path, rec.Tier), v)
	})
}

func (s *Store) GetFile(path string, tier Tier) (FileRecord, error) {
	var rec FileRecord
	err := s.db.View(func(tx *bolt.Tx) error {
		v := tx.Bucket(bucketFiles).Get(key(path, tier))
		if v == nil {
			return os.ErrNotExist
		}
		return json.Unmarshal(v, &rec)
	})
	return rec, err
}

func (s *Store) DeleteFile(path string, tier Tier) error {
	return s.db.Update(func(tx *bolt.Tx) error { return tx.Bucket(bucketFiles).Delete(key(path, tier)) })
}

func (s *Store) MarkEventProcessed(eventID string, ttl time.Duration) error {
	expires := time.Now().Add(ttl).Unix()
	return s.db.Update(func(tx *bolt.Tx) error {
		return tx.Bucket(bucketEvents).Put([]byte(eventID), []byte(fmt.Sprintf("%d", expires)))
	})
}

func (s *Store) IsEventProcessed(eventID string) (bool, error) {
	var raw []byte
	err := s.db.View(func(tx *bolt.Tx) error {
		raw = tx.Bucket(bucketEvents).Get([]byte(eventID))
		return nil
	})
	if err != nil || raw == nil {
		return false, err
	}
	var exp int64
	if _, err := fmt.Sscanf(string(raw), "%d", &exp); err != nil {
		return false, errors.New("bad event expiry")
	}
	return time.Now().Unix() <= exp, nil
}
