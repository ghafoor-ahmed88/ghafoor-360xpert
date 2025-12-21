// ===== Products (Rules) =====
class Transport {
  deliver() {}
}

class Driver {
  drive() {}
}

// ===== Road Family =====
class Truck extends Transport {
  deliver() {
    console.log("Deliver by land (Truck)");
  }
}

class TruckDriver extends Driver {
  drive() {
    console.log("Truck driver driving");
  }
}

// ===== Sea Family =====
class Ship extends Transport {
  deliver() {
    console.log("Deliver by sea (Ship)");
  }
}

class ShipCaptain extends Driver {
  drive() {
    console.log("Ship captain sailing");
  }
}

// ===== Abstract Factory =====
class LogisticsFactory {
  createTransport() {}
  createDriver() {}
}

// ===== Concrete Factories =====
class RoadLogisticsFactory extends LogisticsFactory {
  createTransport() {
    return new Truck();
  }

  createDriver() {
    return new TruckDriver();
  }
}

class SeaLogisticsFactory extends LogisticsFactory {
  createTransport() {
    return new Ship();
  }

  createDriver() {
    return new ShipCaptain();
  }
}

// ===== Client Code =====
function planDelivery(factory) {
  const transport = factory.createTransport();
  const driver = factory.createDriver();

  driver.drive();
  transport.deliver();
}

// ===== Usage =====
planDelivery(new RoadLogisticsFactory());
// Truck driver driving
// Deliver by land (Truck)

planDelivery(new SeaLogisticsFactory());
// Ship captain sailing
// Deliver by sea (Ship)
