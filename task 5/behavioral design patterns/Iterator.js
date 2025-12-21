class Iterator {
  constructor(items) {
    this.items = items;
    this.index = 0;
  }

  hasNext() {
    return this.index < this.items.length;
  }

  next() {
    return this.items[this.index++];
  }
}

// collection
const items = ["Apple", "Banana", "Mango"];
const iterator = new Iterator(items);

// usage
while (iterator.hasNext()) {
  console.log(iterator.next());
}
