<?xml version='1.0' encoding='UTF-8'?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
  <xsl:output omit-xml-declaration="yes"/>
  <xsl:template match="@*|node()">
    <xsl:copy>
      <xsl:apply-templates select="@*|node()"/>
    </xsl:copy>
  </xsl:template>
  <xsl:template match="Culture[@id='sturgia']/@name"><xsl:attribute name="name">{=sturgiafaction}Sturgia</xsl:attribute></xsl:template>
  <xsl:template match="Culture[@id='battania']/@name"><xsl:attribute name="name">{=battaniafaction}Battania</xsl:attribute></xsl:template>
  <xsl:template match="Culture[@id='vlandia']/@name"><xsl:attribute name="name">{=vlandiafaction}Vlandia</xsl:attribute></xsl:template>
  <xsl:template match="Culture[@id='khuzait']/@name"><xsl:attribute name="name">{=khuzaitfaction}Khuzait</xsl:attribute></xsl:template>

</xsl:stylesheet>