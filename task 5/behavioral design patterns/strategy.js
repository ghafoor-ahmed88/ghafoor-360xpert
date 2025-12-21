class CreditCard {
  pay(amount) {
    console.log("Paid via Credit Card:", amount);
  }
}

class PayPal {
  pay(amount) {
    console.log("Paid via PayPal:", amount);
  }
}

class Payment {
  constructor(strategy) {
    this.strategy = strategy;
  }

  makePayment(amount) {
    this.strategy.pay(amount);
  }
}

// runtime pe strategy change
let payment = new Payment(new CreditCard());
payment.makePayment(100);

payment = new Payment(new PayPal());
payment.makePayment(200);