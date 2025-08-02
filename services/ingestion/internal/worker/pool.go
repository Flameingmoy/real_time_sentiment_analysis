package worker

import (
	"context"
	"log"
	"sync"
)

// Job represents a task to be executed by a worker.
// For our case, it will contain the data needed for processing a webhook request.
type Job struct {
	Process func(ctx context.Context)
}

// Worker represents a worker that executes jobs.
// It has a channel to receive jobs and a wait group to signal completion.
type Worker struct {
	ID         int
	JobChannel chan Job
	Quit       chan bool
	Wg         *sync.WaitGroup
}

// NewWorker creates a new worker.
func NewWorker(id int, jobChannel chan Job, wg *sync.WaitGroup) *Worker {
	return &Worker{
		ID:         id,
		JobChannel: jobChannel,
		Quit:       make(chan bool),
		Wg:         wg,
	}
}

// Start begins the worker's job execution loop.
func (w *Worker) Start(ctx context.Context) {
	log.Printf("INFO: Worker %d starting...", w.ID)
	defer w.Wg.Done()
	for {
		select {
		case job := <-w.JobChannel:
			// Execute the job's process function.
			job.Process(ctx)
		case <-w.Quit:
			// We have been asked to stop.
			log.Printf("INFO: Worker %d stopping.", w.ID)
			return
		case <-ctx.Done():
			// Context has been canceled, likely due to server shutdown.
			log.Printf("INFO: Worker %d stopping due to context cancellation.", w.ID)
			return
		}
	}
}

// Stop signals the worker to stop processing new jobs.
func (w *Worker) Stop() {
	go func() {
		w.Quit <- true
	}()
}

// Dispatcher manages the pool of workers and dispatches jobs to them.
type Dispatcher struct {
	JobQueue   chan Job
	MaxWorkers int
	Workers    []*Worker
	Wg         *sync.WaitGroup
	ctx        context.Context
	cancel     context.CancelFunc
}

// NewDispatcher creates a new dispatcher.
func NewDispatcher(maxWorkers int, jobQueueSize int) *Dispatcher {
	jobQueue := make(chan Job, jobQueueSize)
	ctx, cancel := context.WithCancel(context.Background())
	return &Dispatcher{
		JobQueue:   jobQueue,
		MaxWorkers: maxWorkers,
		Wg:         &sync.WaitGroup{},
		ctx:        ctx,
		cancel:     cancel,
	}
}

// Run starts the dispatcher and its workers.
func (d *Dispatcher) Run() {
	log.Printf("INFO: Starting dispatcher with %d workers...", d.MaxWorkers)
	for i := 1; i <= d.MaxWorkers; i++ {
		d.Wg.Add(1)
		worker := NewWorker(i, d.JobQueue, d.Wg)
		d.Workers = append(d.Workers, worker)
		go worker.Start(d.ctx)
	}
}

// Stop gracefully shuts down the dispatcher and all its workers.
func (d *Dispatcher) Stop() {
	log.Printf("INFO: Stopping dispatcher...")
	// Signal all workers to stop.
	for _, worker := range d.Workers {
		worker.Stop()
	}

	// Cancel the context to stop any workers waiting on it.
	d.cancel()

	// Wait for all workers to finish their current jobs and exit.
	d.Wg.Wait()
	log.Printf("INFO: All workers have stopped. Dispatcher shutdown complete.")
}

// Submit adds a new job to the job queue.
func (d *Dispatcher) Submit(job Job) {
	d.JobQueue <- job
}
