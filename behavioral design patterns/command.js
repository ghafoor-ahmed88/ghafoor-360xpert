class Command {
  execute() {
    throw new Error("Execute method must be implemented");
  }
}
class SendEmailCommand extends Command {
  execute() {
    console.log("📧 Email sent to user");
  }
}

class SendSMSCommand extends Command {
  execute() {
    console.log("📱 SMS sent to user");
  }
}

class GenerateReportCommand extends Command {
  execute() {
    console.log("📊 Report generated");
  }
}
class JobQueue {
  constructor() {
    this.jobs = [];
  }

  addJob(command) {
    this.jobs.push(command);
  }

  processJobs() {
    while (this.jobs.length > 0) {
      const job = this.jobs.shift();
      job.execute();
    }
  }
}
const queue = new JobQueue();

queue.addJob(new SendEmailCommand());
queue.addJob(new SendSMSCommand());
queue.addJob(new GenerateReportCommand());

queue.processJobs();
