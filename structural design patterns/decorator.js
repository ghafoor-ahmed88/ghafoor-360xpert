// Base Component
class Notifier {
  send(message) {
    console.log("Email sent:", message);
  }
}

// Base Decorator
class NotifierDecorator {
  constructor(notifier) {
    this.notifier = notifier; // object ka reference
  }

  send(message) {
    this.notifier.send(message);
  }
}

// Concrete Decorator - SMS
class SMSDecorator extends NotifierDecorator {
  send(message) {
    super.send(message);
    console.log("SMS sent:", message);
  }
}

// Concrete Decorator - Slack
class SlackDecorator extends NotifierDecorator {
  send(message) {
    super.send(message);
    console.log("Slack message sent:", message);
  }
}

// ===== Usage =====
let notifier = new Notifier();          // base object
notifier = new SMSDecorator(notifier);  // wrap with SMS
notifier = new SlackDecorator(notifier); // wrap with Slack

notifier.send("Server is on!");
