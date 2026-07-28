// SmokeTests.cs — EditMode smoke 테스트. NUnit + asmdef 정상 동작 검증용 standalone.
// 메인 코드(Assembly-CSharp) 의존 없음. 통과 = Test Runner 파이프라인 OK.
using NUnit.Framework;

namespace URHYNIX.ControlRoom.Tests.EditMode
{
    public class SmokeTests
    {
        [Test]
        public void Math_BasicAddition_Passes()
        {
            Assert.AreEqual(2, 1 + 1);
        }

        [Test]
        public void String_NotNullOrEmpty()
        {
            Assert.IsNotNull("hello");
            Assert.IsNotEmpty("hello");
        }

        [Test]
        public void Float_TolerantEquality()
        {
            Assert.AreEqual(0.1f + 0.2f, 0.3f, 1e-6);
        }
    }
}
