using System.Linq;
using Microsoft.AspNetCore.Mvc;

namespace TestAppDotnet.Controllers
{
	[Route("/healthcheck")]
	[ApiController]
	public class HealthcheckController : ControllerBase
	{
		[HttpGet()]
		public ActionResult<string> Get() => "OK";
	}
}
