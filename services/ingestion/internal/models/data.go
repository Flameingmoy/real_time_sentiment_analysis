package models

import "time"

// TrueData represents the structure for TrueData webhooks
type TrueData struct {
	ID        string    `json:"id" binding:"required"`
	Symbol    string    `json:"symbol" binding:"required"`
	Price     float64   `json:"price" binding:"required"`
	Volume    int64     `json:"volume" binding:"required"`
	Timestamp time.Time `json:"timestamp" binding:"required"`
}

// NewsArticle represents the structure for news API webhooks
type NewsArticle struct {
	ID        string    `json:"id" binding:"required"`
	Source    string    `json:"source" binding:"required"`
	Headline  string    `json:"headline" binding:"required"`
	Summary   string    `json:"summary"`
	URL       string    `json:"url" binding:"required,url"`
	Timestamp time.Time `json:"timestamp" binding:"required"`
}

// Tweet represents the structure for Twitter API webhooks
type Tweet struct {
	ID        string    `json:"id" binding:"required"`
	User      string    `json:"user" binding:"required"`
	Text      string    `json:"text" binding:"required"`
	Likes     int       `json:"likes"`
	Retweets  int       `json:"retweets"`
	Timestamp time.Time `json:"timestamp" binding:"required"`
}
