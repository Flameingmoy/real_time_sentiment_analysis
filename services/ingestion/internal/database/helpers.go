package database

import (
	"bytes"
	"encoding/json"
	"sort"
)

// marshalSorted marshals a map[string]interface{} to a JSON byte slice with sorted keys.
// This is crucial for creating a consistent hash of the content.
func marshalSorted(m map[string]interface{}) ([]byte, error) {
	if m == nil {
		return []byte("null"), nil
	}

	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)

	var buf bytes.Buffer
	buf.WriteByte('{')
	encoder := json.NewEncoder(&buf)

	for i, k := range keys {
		// Add comma before each element except the first
		if i > 0 {
			buf.WriteByte(',')
		}

		// Marshal key
		if err := encoder.Encode(k); err != nil {
			return nil, err
		}
		// Replace the newline that Encode adds with a colon
		buf.Truncate(buf.Len() - 1)
		buf.WriteByte(':')

		// Marshal value
		valueBytes, err := json.Marshal(m[k])
		if err != nil {
			return nil, err
		}
		buf.Write(valueBytes)
	}

	buf.WriteByte('}')
	return buf.Bytes(), nil
}
