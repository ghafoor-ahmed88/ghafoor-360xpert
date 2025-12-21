// State 1
class SilentMode {
  ring() {
    console.log("Phone is silent 🤫");
  }
}

// State 2
class NormalMode {
  ring() {
    console.log("Phone is ringing 🔔");
  }
}

// Context
class Phone {
  setState(state) {
    this.state = state;
  }

  ring() {
    this.state.ring();
  }
}

// usage
const phone = new Phone();

phone.setState(new SilentMode());
phone.ring();

phone.setState(new NormalMode());
phone.ring();
