class SonyTV {
  on() {
    console.log("Sony TV ON");
  }
}

class SamsungTV {
  on() {
    console.log("Samsung TV ON");
  }
}
class Remote {
  constructor(tv) {
    this.tv = tv; // 🔗 YAHI BRIDGE HAI
  }

  pressOn() {
    this.tv.on();
  }
}
const sonyRemote = new Remote(new SonyTV());
sonyRemote.pressOn();

const samsungRemote = new Remote(new SamsungTV());
samsungRemote.pressOn();
