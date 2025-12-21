// SUBJECT (Observable)
class NewsAgency {
  constructor() {
    this.observers = []; // list of observers
  }

  subscribe(observer) {
    this.observers.push(observer);
  }

  unsubscribe(observer) {
    this.observers = this.observers.filter(o => o !== observer);
  }

  notify(news) {
    for (let observer of this.observers) {
      observer.update(news);
    }
  }

  publishNews(news) {
    console.log("\nNews Published:", news);
    this.notify(news);
  }
}

// OBSERVER
class NewsChannel {
  constructor(name) {
    this.name = name;
  }

  update(news) {
    console.log(`${this.name} received news: ${news}`);
  }
}

// CLIENT CODE
const agency = new NewsAgency();

const geo = new NewsChannel("Geo News");
const ary = new NewsChannel("ARY News");
const bbc = new NewsChannel("BBC News");

agency.subscribe(geo);
agency.subscribe(ary);
agency.subscribe(bbc);

agency.publishNews("Observer Pattern Explained");

agency.unsubscribe(ary);

agency.publishNews("Breaking News: Design Patterns Easy");
